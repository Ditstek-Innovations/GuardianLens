"""RTSP camera ingestion — MOD-1 Stream Manager, live form (TRD 4).

One :class:`RtspSource` manages one camera and implements the MOD-1
failure-handling row EXACTLY:

* Connection loss → reconnect with exponential backoff (1s, 2s, 4s …
  capped 60s), **unlimited retries**. The loss is reported to the injected
  :class:`StreamStatusListener` so a coverage gap opens with reason
  ``stream_lost`` and closes on restore — gaps are recorded, never
  inferred (FR-005, ARCHITECTURE.md 6.5 RS-5). A camera that never
  connects is exactly as unwatched as one that dropped, so failure to
  establish the first connection reports loss too.
* Decode error on a single frame → drop the frame, increment a counter,
  continue.
* Sustained decode failure past ``decode_failure_threshold`` consecutive
  errors → report the camera degraded (alert), keep going. The threshold
  is ``[OPEN]`` — MOD-1 says "> threshold" and no document states a value,
  and BACKEND_CODING_RULES 4 forbids resolving ``[OPEN]`` by assumption —
  so it is a required constructor parameter with no default.

Sampling (TRD 5.2): the driver buffer is drained by calling ``grab()``
continuously; ``retrieve()`` (the expensive decode) happens only at sample
instants, ``1 / sample_rate_fps`` apart. Without the continuous drain the
RTSP client buffers every frame the camera pushes and playback lag grows
without bound.

``captured_at`` is stamped from the edge clock at retrieve time (ADR-007)
and the frame carries the JPEG bytes of the sampled image in memory —
never written to disk here (DATABASE.md 11.5; only the event builder
spools bytes, and only for admitted candidates).

cv2 is imported lazily, exactly like ``VideoFileSource``: the synthetic
path and every unit test run with zero vision dependencies. Unit tests
inject a fake capture factory, encoder, clock and sleep.

The stream URL embeds the camera credential, so this module never logs it
and ``repr(RtspSource)`` redacts it (see ``unsealer.UnsealedStreamUrl``).
"""

from __future__ import annotations

import logging
import subprocess
import threading
import time
from datetime import datetime, timezone
from typing import Callable, Iterator, Protocol
from urllib.parse import urlsplit

from guardian_lens_edge.frames import Frame
from guardian_lens_edge.unsealer import UnsealedStreamUrl

__all__ = [
    "CaptureLike",
    "RtspSource",
    "StreamStatusListener",
    "diagnose_rtsp_open_failure",
    "redacted_rtsp_target",
]

logger = logging.getLogger(__name__)

_RTSP_REF_PREFIX = "rtsp:"

#: Default cv2/FFmpeg socket timeouts. Without them a dead TCP peer blocks
#: ``grab()`` indefinitely and the reconnect logic never runs.
_OPEN_TIMEOUT_MS = 5_000
_READ_TIMEOUT_MS = 5_000


class CaptureLike(Protocol):
    """The slice of ``cv2.VideoCapture`` this module uses."""

    def isOpened(self) -> bool:  # noqa: N802 - cv2 spelling
        ...

    def grab(self) -> bool:
        ...

    def retrieve(self) -> tuple[bool, object]:
        ...

    def release(self) -> None:
        ...


class StreamStatusListener(Protocol):
    """Where MOD-1 stream conditions land (IF: ``StreamHealth`` to MOD-4).

    The wiring routes these into the existing gap mechanics (RS-5):
    ``stream_lost`` opens a ``stream_lost`` coverage gap for the camera;
    ``stream_restored`` and ``stream_connected`` close it; and
    ``stream_degraded`` raises the MOD-1 sustained-decode-failure alert.
    """

    def stream_connected(self, camera_id: str, at: datetime) -> None:
        """First successful connection (no loss was pending)."""
        ...

    def stream_lost(self, camera_id: str, at: datetime) -> None:
        ...

    def stream_restored(self, camera_id: str, at: datetime) -> None:
        ...

    def stream_degraded(self, camera_id: str, at: datetime) -> None:
        ...


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def redacted_rtsp_target(url: str) -> str:
    """Host/path only — never userinfo. Safe for logs."""
    parts = urlsplit(url)
    if not parts.hostname:
        return "unparseable RTSP URL (missing host; need rtsp://ip:port/path)"
    port = f":{parts.port}" if parts.port is not None else ""
    path = parts.path or "/"
    kind = "with camera login" if parts.username else "no camera login"
    scheme = parts.scheme or "rtsp"
    return f"{scheme}://{parts.hostname}{port}{path} ({kind})"


def _scrub_secrets(text: str, url: str) -> str:
    parts = urlsplit(url)
    cleaned = text.replace(url, "<stream>")
    if parts.password:
        cleaned = cleaned.replace(parts.password, "***")
    if parts.username:
        cleaned = cleaned.replace(parts.username, "***")
    return cleaned


def diagnose_rtsp_open_failure(url: str) -> str:
    """Ask ffmpeg why OpenCV could not open the stream. Never returns the URL."""
    try:
        proc = subprocess.run(
            [
                "ffmpeg",
                "-hide_banner",
                "-loglevel",
                "error",
                "-rtsp_transport",
                "tcp",
                "-stimeout",
                "3000000",
                "-i",
                url,
                "-frames:v",
                "1",
                "-f",
                "null",
                "-",
            ],
            capture_output=True,
            text=True,
            timeout=8,
        )
    except FileNotFoundError:
        return "OpenCV could not open the stream (ffmpeg not installed for a detailed reason)"
    except subprocess.TimeoutExpired:
        return "RTSP timed out — camera did not deliver a frame"
    raw = _scrub_secrets((proc.stderr or "") + (proc.stdout or ""), url)
    lowered = raw.lower()
    if "401" in raw or "unauthorized" in lowered:
        return (
            "camera returned 401 Unauthorized — this URL has no working login; "
            "enable anonymous RTSP on the camera or replace the stored URL with one that includes credentials"
        )
    if "403" in raw or "forbidden" in lowered:
        return "camera returned 403 Forbidden"
    if "404" in raw or "not found" in lowered:
        return "camera returned 404 — RTSP path is wrong (try stream1/stream2)"
    if "no route" in lowered or "network is unreachable" in lowered:
        return "no route to host — camera IP is not reachable from this machine"
    if "connection refused" in lowered:
        return "connection refused — nothing is listening on that RTSP port"
    if "timed out" in lowered or "timeout" in lowered:
        return "connection timed out — camera did not answer"
    if "no such file" in lowered:
        return "unparseable stream URL (missing rtsp://host/path)"
    line = next((part.strip() for part in raw.splitlines() if part.strip()), "")
    if line:
        return line[:300]
    return "OpenCV could not open the stream"


def _default_capture_factory(url: str) -> CaptureLike:
    try:
        import cv2  # noqa: PLC0415 — lazy on purpose, see module docstring
    except ImportError as exc:
        raise RuntimeError(
            "RtspSource requires opencv-python-headless (cv2), which is "
            "not installed. It is intentionally an optional dependency "
            "(pyproject [edge-camera]); the synthetic path needs no vision "
            "dependencies (TRD 13.2)."
        ) from exc
    return cv2.VideoCapture(
        url,
        cv2.CAP_FFMPEG,
        [
            cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, _OPEN_TIMEOUT_MS,
            cv2.CAP_PROP_READ_TIMEOUT_MSEC, _READ_TIMEOUT_MS,
        ],
    )


def _default_jpeg_encoder(image: object) -> bytes:
    import cv2  # noqa: PLC0415 — lazy on purpose, see module docstring

    is_encoded, buffer = cv2.imencode(".jpg", image)
    if not is_encoded:
        raise ValueError("cv2.imencode returned failure")
    return buffer.tobytes()


class RtspSource:
    """MOD-1 for one camera. See the module docstring for the behaviour.

    All effectful collaborators are injected so unit tests are wall-clock
    free: ``capture_factory`` replaces ``cv2.VideoCapture``,
    ``jpeg_encoder`` replaces ``cv2.imencode``, ``monotonic`` drives the
    sampling cadence, ``utc_now`` stamps ``captured_at`` and ``sleep``
    absorbs the backoff. The default sleep waits on the internal stop
    event, so ``stop()`` interrupts a pending backoff immediately.
    """

    def __init__(
        self,
        camera_id: str,
        stream_url: UnsealedStreamUrl,
        *,
        sample_rate_fps: float,
        decode_failure_threshold: int,
        listener: StreamStatusListener,
        capture_factory: Callable[[str], CaptureLike] | None = None,
        jpeg_encoder: Callable[[object], bytes] | None = None,
        monotonic: Callable[[], float] = time.monotonic,
        utc_now: Callable[[], datetime] = _utc_now,
        sleep: Callable[[float], None] | None = None,
        backoff_base_seconds: float = 1.0,
        backoff_cap_seconds: float = 60.0,
        open_diagnoser: Callable[[str], str] | None = None,
    ) -> None:
        if sample_rate_fps <= 0:
            raise ValueError("sample_rate_fps must be positive")
        if decode_failure_threshold <= 0:
            raise ValueError(
                "decode_failure_threshold must be positive; it is [OPEN] "
                "and must be stated explicitly by the deployment"
            )
        if backoff_base_seconds <= 0 or backoff_cap_seconds < backoff_base_seconds:
            raise ValueError("invalid backoff parameters")
        self._camera_id = camera_id
        self._stream_url = stream_url
        self._sample_interval = 1.0 / sample_rate_fps
        self._decode_failure_threshold = decode_failure_threshold
        self._listener = listener
        self._capture_factory = capture_factory or _default_capture_factory
        self._jpeg_encoder = jpeg_encoder or _default_jpeg_encoder
        self._monotonic = monotonic
        self._utc_now = utc_now
        self._stop_event = threading.Event()
        self._sleep = sleep or self._stop_event.wait
        self._backoff_base = backoff_base_seconds
        self._backoff_cap = backoff_cap_seconds
        self._open_diagnoser = open_diagnoser
        # Counters and state, readable by wiring/health.
        self._decode_errors_total = 0
        self._consecutive_decode_failures = 0
        self._degraded_reported = False
        self._loss_pending = False
        self._sequence = 0
        # Persists across reconnect attempts within one outage; reset only
        # when frames actually flow again (see _on_streaming_established).
        self._backoff_attempt = 0

    # ------------------------------------------------------------------
    # Introspection
    # ------------------------------------------------------------------

    @property
    def camera_id(self) -> str:
        return self._camera_id

    @property
    def decode_errors_total(self) -> int:
        """MOD-1: a dropped frame is counted, never silently discarded."""
        return self._decode_errors_total

    def __repr__(self) -> str:
        # The URL embeds the camera credential: redacted, always.
        return (
            f"RtspSource(camera_id={self._camera_id!r}, "
            "stream_url=<redacted>)"
        )

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def stop(self) -> None:
        """Ask the ``frames()`` loop to exit; interrupts a pending backoff."""
        self._stop_event.set()

    @property
    def stopped(self) -> bool:
        return self._stop_event.is_set()

    # ------------------------------------------------------------------
    # FrameSource
    # ------------------------------------------------------------------

    def frames(self) -> Iterator[Frame]:
        """Yield sampled frames until ``stop()``; reconnects forever."""
        while not self._stop_event.is_set():
            capture = self._connect_with_backoff()
            if capture is None:
                return  # stopped during (re)connect
            try:
                yield from self._stream(capture)
            finally:
                capture.release()
        # stop() during streaming falls through here.

    # ------------------------------------------------------------------
    # Connection management
    # ------------------------------------------------------------------

    def _connect_with_backoff(self) -> CaptureLike | None:
        """Open the stream, retrying forever: 1s, 2s, 4s … capped (MOD-1).

        An open capture is NOT yet a working stream — some RTSP servers
        accept the session while no frames are being published — so
        connected/restored is reported by ``_stream`` on the first
        successful ``grab``, and the backoff attempt counter keeps growing
        until then. Otherwise an accepts-but-never-delivers server would
        pin the retry loop at the 1-second floor and spam spurious
        restored/lost transitions (gap churn) for the whole outage.
        """
        while not self._stop_event.is_set():
            capture = self._capture_factory(self._stream_url.reveal())
            if capture.isOpened():
                return capture
            capture.release()
            self._report_loss_once()
            if self._backoff_attempt == 0 and self._open_diagnoser is not None:
                logger.warning(
                    "camera %s: connect failed targeting %s — %s",
                    self._camera_id,
                    redacted_rtsp_target(self._stream_url.reveal()),
                    self._open_diagnoser(self._stream_url.reveal()),
                )
            self._backoff_sleep("connect failed")
        return None

    def _backoff_sleep(self, why: str) -> None:
        delay = min(
            self._backoff_cap,
            self._backoff_base * (2 ** self._backoff_attempt),
        )
        self._backoff_attempt += 1
        logger.warning(
            "camera %s: %s targeting %s (attempt %d), retrying in %.0fs",
            self._camera_id,
            why,
            redacted_rtsp_target(self._stream_url.reveal()),
            self._backoff_attempt,
            delay,
        )
        self._sleep(delay)

    def _on_streaming_established(self) -> None:
        """First successful grab of a connection: frames are flowing."""
        now = self._utc_now()
        self._backoff_attempt = 0
        # A new connection starts a fresh decode streak; the total counter
        # is cumulative on purpose.
        self._consecutive_decode_failures = 0
        self._degraded_reported = False
        if self._loss_pending:
            self._loss_pending = False
            logger.info("camera %s: stream restored", self._camera_id)
            self._listener.stream_restored(self._camera_id, now)
        else:
            logger.info("camera %s: stream connected", self._camera_id)
            self._listener.stream_connected(self._camera_id, now)

    def _report_loss_once(self) -> None:
        if self._loss_pending:
            return
        self._loss_pending = True
        logger.warning("camera %s: stream lost", self._camera_id)
        self._listener.stream_lost(self._camera_id, self._utc_now())

    # ------------------------------------------------------------------
    # Streaming
    # ------------------------------------------------------------------

    def _stream(self, capture: CaptureLike) -> Iterator[Frame]:
        """Grab continuously; retrieve only at sample instants.

        Returns (without raising) on connection loss so ``frames()``
        re-enters the backoff loop.
        """
        established = False
        next_sample_at = self._monotonic()  # first frame sampled at once
        while not self._stop_event.is_set():
            if not capture.grab():
                # The driver could not advance the stream: connection lost.
                self._report_loss_once()
                if not established:
                    # Session opened but no frame ever arrived: this is
                    # still the same outage — keep the backoff growing.
                    self._backoff_sleep("stream opened but delivered nothing")
                return
            if not established:
                established = True
                self._on_streaming_established()
            if self._monotonic() < next_sample_at:
                continue  # drained, not sampled — no decode cost
            frame = self._retrieve_sample(capture)
            next_sample_at = self._monotonic() + self._sample_interval
            if frame is not None:
                yield frame

    def _retrieve_sample(self, capture: CaptureLike) -> Frame | None:
        """Decode one sample; MOD-1 single-frame failure row on error."""
        try:
            is_decoded, image = capture.retrieve()
            if not is_decoded or image is None:
                raise ValueError("retrieve returned no image")
            jpeg_bytes = self._jpeg_encoder(image)
        except Exception as exc:  # noqa: BLE001 — MOD-1: drop frame,
            # increment counter, continue; sustained failure degrades.
            self._record_decode_error(exc)
            return None
        captured_at = self._utc_now()  # edge clock at retrieve time, ADR-007
        if self._consecutive_decode_failures > 0:
            logger.info(
                "camera %s: decode recovered after %d consecutive failures",
                self._camera_id,
                self._consecutive_decode_failures,
            )
        self._consecutive_decode_failures = 0
        self._degraded_reported = False
        sequence = self._sequence
        self._sequence += 1
        # Heartbeat, not every frame: 2 fps × N cameras would drown the log.
        # First sample plus every 30th proves capture is alive and sized.
        if sequence == 0 or sequence % 30 == 0:
            logger.info(
                "camera %s: captured JPEG sample seq=%d bytes=%d at=%s",
                self._camera_id,
                sequence,
                len(jpeg_bytes),
                captured_at.isoformat(),
            )
        return Frame(
            camera_id=self._camera_id,
            captured_at=captured_at,
            image_ref=f"{_RTSP_REF_PREFIX}{self._camera_id}:{sequence}",
            sequence=sequence,
            image_bytes=jpeg_bytes,
        )

    def _record_decode_error(self, exc: Exception) -> None:
        self._decode_errors_total += 1
        self._consecutive_decode_failures += 1
        logger.warning(
            "camera %s: frame decode error dropped (total=%d streak=%d): %s",
            self._camera_id,
            self._decode_errors_total,
            self._consecutive_decode_failures,
            exc,
        )
        if (
            self._consecutive_decode_failures > self._decode_failure_threshold
            and not self._degraded_reported
        ):
            # MOD-1: sustained decode failure > threshold -> degraded, alert.
            # Reported once per streak; a good frame re-arms it.
            self._degraded_reported = True
            self._listener.stream_degraded(self._camera_id, self._utc_now())
