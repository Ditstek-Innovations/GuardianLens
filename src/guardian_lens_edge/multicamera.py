"""Multi-camera composition: N RtspSources → one consumable frame stream.

Why a dedicated class instead of per-camera wiring inside ``agent.py``:
``EdgeAgent.process_frame`` is already per-frame and camera-agnostic, so
the agent needs exactly one thing from the camera plane — "the next
sampled frame, from whichever camera has one". Concentrating the threads,
the bounded queue and the rebuild-on-config-change logic here keeps every
threading concern out of the agent (whose ticks stay deterministic and
steppable) and gives backpressure exactly one implementation point. It
also makes the wiring testable with fake sources and no cv2.

Threading model — one pump thread per camera, one consumer:

* Each configured camera gets an :class:`~guardian_lens_edge.rtsp.RtspSource`
  (credential unsealed at composition time via ``CredentialUnsealer``,
  held in memory only) and a daemon thread iterating ``source.frames()``
  into a shared **bounded** queue.
* Bounded means backpressure: when the consumer falls behind and the
  queue is full, the arriving (NEWEST) sample is dropped and counted —
  the pump never blocks, so a slow main loop can never make a camera
  thread stop draining its RTSP buffer, and the queue keeps the oldest
  not-yet-processed samples so event ``occurred_at`` ordering is
  preserved.
* Stream status callbacks (lost / restored / connected / degraded) are
  raised on camera threads, but the edge store's SQLite connection is
  single-threaded — so they are queued as status events and dispatched to
  the real listener on the CONSUMER thread, inside ``next_frame`` /
  ``apply_config`` / ``close``. Status events are never dropped: gaps are
  recorded, never inferred (FR-005).

A camera whose credential cannot be unsealed (wrong key id, dev
placeholder, corrupt ciphertext) is not started; the failure is logged as
an ERROR naming the camera and reported as ``stream_lost`` so a coverage
gap opens — a camera that is configured for monitoring and cannot be
watched is exactly what a gap records. The camera is retried on the next
configuration change, so key rotation heals it without a restart.
"""

from __future__ import annotations

import enum
import logging
import queue
import threading
from collections import deque
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable, Iterator, Protocol, runtime_checkable

from guardian_lens_edge.config import AgentConfig, CameraConfig
from guardian_lens_edge.frames import Frame
from guardian_lens_edge.rtsp import (
    RtspSource,
    StreamStatusListener,
    diagnose_rtsp_open_failure,
)
from guardian_lens_edge.state import STREAM_LOST_REASON, GapRecorder
from guardian_lens_edge.unsealer import (
    CredentialUnsealError,
    CredentialUnsealer,
    UnsealedStreamUrl,
)

__all__ = [
    "CameraStreamSpec",
    "LiveFrameSource",
    "MultiCameraSource",
    "StreamGapRouter",
]

logger = logging.getLogger(__name__)

#: Frame-queue capacity. A loop mechanic (roughly: seconds of buffered
#: samples across cameras before drop-newest engages), not an `[OPEN]`
#: product threshold — so a sane dev default is appropriate here.
DEFAULT_QUEUE_CAPACITY = 64

_THREAD_JOIN_TIMEOUT_SECONDS = 10.0


class StreamGapRouter:
    """Routes MOD-1 stream conditions into the EXISTING gap mechanics.

    Uses the same :class:`~guardian_lens_edge.state.GapRecorder` as the
    ADR-009 state machine, so ``stream_lost`` gaps share the open/close
    wire shape and idempotency keys with halt gaps (RS-5). Not
    thread-safe by design: :class:`MultiCameraSource` dispatches to it on
    the consumer thread only.
    """

    def __init__(self, recorder: GapRecorder) -> None:
        self._recorder = recorder

    def stream_connected(self, camera_id: str, at: datetime) -> None:
        # Closes any stream_lost gap left by a composition-time failure
        # (e.g. a credential fixed by key rotation): idempotent no-op when
        # nothing is open.
        self._close_stream_gaps(camera_id, at)

    def stream_lost(self, camera_id: str, at: datetime) -> None:
        if self._recorder.open_for(camera_id, STREAM_LOST_REASON):
            return  # already recorded; a gap opens once, closes once
        gap_id = self._recorder.open(camera_id, STREAM_LOST_REASON, at)
        logger.warning(
            "coverage gap opened: camera=%s reason=%s gap_id=%s",
            camera_id,
            STREAM_LOST_REASON,
            gap_id,
        )

    def stream_restored(self, camera_id: str, at: datetime) -> None:
        self._close_stream_gaps(camera_id, at)

    def stream_degraded(self, camera_id: str, at: datetime) -> None:
        # MOD-1: sustained decode failure > threshold -> degraded, alert.
        # The alert is this ERROR line (ADR-010: support sees only what the
        # agent chooses to report); the stream stays up, so no gap opens.
        logger.error(
            "camera %s DEGRADED at %s: sustained frame decode failure — "
            "stream connected but frames are not decodable",
            camera_id,
            at.isoformat(timespec="seconds"),
        )

    def _close_stream_gaps(self, camera_id: str, at: datetime) -> None:
        for gap in self._recorder.open_for(camera_id, STREAM_LOST_REASON):
            self._recorder.close(gap, at)


@dataclass(frozen=True)
class CameraStreamSpec:
    """What MOD-1 needs to run one camera, exactly as configured.

    Equality over these fields is the rebuild trigger: a camera whose spec
    is unchanged across a config version keeps its running source.
    """

    camera_id: str
    sample_rate_fps: float
    stream_url_sealed: str | None
    stream_url_key_id: str | None

    @classmethod
    def from_camera(cls, camera: CameraConfig) -> "CameraStreamSpec":
        return cls(
            camera_id=camera.camera_id,
            sample_rate_fps=camera.sample_rate_fps,
            stream_url_sealed=camera.stream_url_sealed,
            stream_url_key_id=camera.stream_url_key_id,
        )


class LiveSource(Protocol):
    """What MultiCameraSource requires of a per-camera source."""

    def frames(self) -> Iterator[Frame]:
        ...

    def stop(self) -> None:
        ...


@runtime_checkable
class LiveFrameSource(Protocol):
    """What the live run loop requires of its frame source.

    ``MultiCameraSource`` is the production implementation; tests inject
    fakes.
    """

    def next_frame(self, timeout: float) -> Frame | None:
        ...

    def apply_config(self, config: AgentConfig | None, now: datetime) -> None:
        ...

    def close(self) -> None:
        ...


#: Builds the per-camera source. Injected in tests (no cv2); the default
#: builds a real RtspSource.
SourceFactory = Callable[
    [CameraStreamSpec, UnsealedStreamUrl, StreamStatusListener], LiveSource
]


class _StatusKind(enum.Enum):
    CONNECTED = "connected"
    LOST = "lost"
    RESTORED = "restored"
    DEGRADED = "degraded"


class _QueueingListener:
    """Listener handed to camera threads: append-only, no store access."""

    def __init__(
        self, events: "deque[tuple[_StatusKind, str, datetime]]"
    ) -> None:
        self._events = events

    def stream_connected(self, camera_id: str, at: datetime) -> None:
        self._events.append((_StatusKind.CONNECTED, camera_id, at))

    def stream_lost(self, camera_id: str, at: datetime) -> None:
        self._events.append((_StatusKind.LOST, camera_id, at))

    def stream_restored(self, camera_id: str, at: datetime) -> None:
        self._events.append((_StatusKind.RESTORED, camera_id, at))

    def stream_degraded(self, camera_id: str, at: datetime) -> None:
        self._events.append((_StatusKind.DEGRADED, camera_id, at))


@dataclass
class _RunningCamera:
    spec: CameraStreamSpec
    source: LiveSource
    thread: threading.Thread


class MultiCameraSource:
    """One frame stream over all configured cameras. See module docstring.

    ``decode_failure_threshold`` is forwarded to every RtspSource and is
    `[OPEN]` — required, no default (see ``rtsp.py``).

    Consumer-thread contract: ``next_frame``, ``frames``, ``apply_config``
    and ``close`` must all be called from the same (main-loop) thread.
    """

    def __init__(
        self,
        *,
        unsealer: CredentialUnsealer,
        status_listener: StreamStatusListener,
        decode_failure_threshold: int,
        queue_capacity: int = DEFAULT_QUEUE_CAPACITY,
        source_factory: SourceFactory | None = None,
    ) -> None:
        if queue_capacity <= 0:
            raise ValueError("queue_capacity must be positive")
        self._unsealer = unsealer
        self._status_listener = status_listener
        self._decode_failure_threshold = decode_failure_threshold
        self._frame_queue: "queue.Queue[Frame]" = queue.Queue(
            maxsize=queue_capacity
        )
        self._status_events: "deque[tuple[_StatusKind, str, datetime]]" = (
            deque()
        )
        self._camera_listener = _QueueingListener(self._status_events)
        self._source_factory = source_factory or self._build_rtsp_source
        self._cameras: dict[str, _RunningCamera] = {}
        self._dropped_lock = threading.Lock()
        self._dropped_frames: dict[str, int] = {}
        self._closed = False

    # ------------------------------------------------------------------
    # Introspection
    # ------------------------------------------------------------------

    @property
    def running_camera_ids(self) -> list[str]:
        return sorted(self._cameras)

    def dropped_frames(self) -> dict[str, int]:
        """Backpressure drops per camera — counted, never silent."""
        with self._dropped_lock:
            return dict(self._dropped_frames)

    def __repr__(self) -> str:
        # Never the URLs: they carry credentials.
        return (
            f"MultiCameraSource(cameras={self.running_camera_ids!r}, "
            f"closed={self._closed})"
        )

    # ------------------------------------------------------------------
    # Configuration
    # ------------------------------------------------------------------

    def apply_config(self, config: AgentConfig | None, now: datetime) -> None:
        """Rebuild sources for added / removed / changed cameras.

        Unchanged cameras keep their running source and connection. Must
        be called on the consumer thread (it dispatches status events).
        """
        if self._closed:
            raise RuntimeError("MultiCameraSource is closed")
        self._dispatch_status_events()
        desired = {
            camera.camera_id: CameraStreamSpec.from_camera(camera)
            for camera in (config.cameras if config else [])
        }
        for camera_id in list(self._cameras):
            running = self._cameras[camera_id]
            if desired.get(camera_id) == running.spec:
                continue  # unchanged — keep streaming
            self._stop_camera(camera_id)
            if camera_id not in desired:
                # Removed from configuration: monitoring responsibility
                # ended, so this is not a coverage gap; any still-open
                # stream_lost gap is left for the control plane to
                # reconcile with the camera's lifecycle.
                logger.info("camera %s removed from configuration", camera_id)
        for camera_id, spec in desired.items():
            if camera_id in self._cameras:
                continue
            self._start_camera(spec, now)

    def _start_camera(self, spec: CameraStreamSpec, now: datetime) -> None:
        if not spec.stream_url_sealed or not spec.stream_url_key_id:
            logger.error(
                "camera %s has no sealed stream URL in its configuration; "
                "it cannot be ingested — recording a coverage gap",
                spec.camera_id,
            )
            self._status_listener.stream_lost(spec.camera_id, now)
            return
        try:
            stream_url = self._unsealer.unseal(
                spec.stream_url_sealed, spec.stream_url_key_id
            )
        except CredentialUnsealError as exc:
            # Loud, attributed, and recorded: configured-but-unwatchable is
            # exactly what a coverage gap exists to say. Retried on the
            # next configuration change.
            logger.error(
                "camera %s credential cannot be unsealed; camera not "
                "started — recording a coverage gap: %s",
                spec.camera_id,
                exc,
            )
            self._status_listener.stream_lost(spec.camera_id, now)
            return
        source = self._source_factory(spec, stream_url, self._camera_listener)
        thread = threading.Thread(
            target=self._pump,
            args=(spec.camera_id, source),
            name=f"gl-camera-{spec.camera_id}",
            daemon=True,
        )
        self._cameras[spec.camera_id] = _RunningCamera(spec, source, thread)
        thread.start()
        logger.info(
            "camera %s started: sample_rate_fps=%s",
            spec.camera_id,
            spec.sample_rate_fps,
        )

    def _build_rtsp_source(
        self,
        spec: CameraStreamSpec,
        stream_url: UnsealedStreamUrl,
        listener: StreamStatusListener,
    ) -> RtspSource:
        return RtspSource(
            spec.camera_id,
            stream_url,
            sample_rate_fps=spec.sample_rate_fps,
            decode_failure_threshold=self._decode_failure_threshold,
            listener=listener,
            open_diagnoser=diagnose_rtsp_open_failure,
        )

    def _stop_camera(self, camera_id: str) -> None:
        running = self._cameras.pop(camera_id)
        running.source.stop()
        running.thread.join(timeout=_THREAD_JOIN_TIMEOUT_SECONDS)
        if running.thread.is_alive():  # pragma: no cover - timing-dependent
            # Daemon thread: it cannot outlive the process. Loud, not hung.
            logger.warning(
                "camera %s pump thread did not stop within %.0fs; abandoned",
                camera_id,
                _THREAD_JOIN_TIMEOUT_SECONDS,
            )

    # ------------------------------------------------------------------
    # Pump threads (one per camera)
    # ------------------------------------------------------------------

    def _pump(self, camera_id: str, source: LiveSource) -> None:
        try:
            for frame in source.frames():
                try:
                    self._frame_queue.put_nowait(frame)
                except queue.Full:
                    # Backpressure: drop the NEWEST sample (this one) and
                    # count it. Never block — blocking here would stop the
                    # RTSP drain and grow driver-side lag unboundedly.
                    self._count_drop(camera_id)
        except Exception:  # noqa: BLE001 — a dead pump must be loud, and an
            # exception on a daemon thread would otherwise vanish.
            logger.exception("camera %s pump thread crashed", camera_id)
            self._camera_listener.stream_lost(
                camera_id, datetime.now(timezone.utc)
            )

    def _count_drop(self, camera_id: str) -> None:
        with self._dropped_lock:
            count = self._dropped_frames.get(camera_id, 0) + 1
            self._dropped_frames[camera_id] = count
        if count == 1 or count % 100 == 0:
            logger.warning(
                "frame queue full: dropped newest sample from camera %s "
                "(dropped=%d)",
                camera_id,
                count,
            )

    # ------------------------------------------------------------------
    # Consumption (main loop thread)
    # ------------------------------------------------------------------

    def next_frame(self, timeout: float) -> Frame | None:
        """The next sampled frame from any camera, or None on timeout.

        Dispatches pending stream-status events first, so gap open/close
        ordering follows observation ordering.
        """
        self._dispatch_status_events()
        try:
            return self._frame_queue.get(timeout=timeout)
        except queue.Empty:
            return None

    def frames(self) -> Iterator[Frame]:
        """FrameSource conformance: yields until ``close()`` is called."""
        while not self._closed:
            frame = self.next_frame(timeout=0.25)
            if frame is not None:
                yield frame

    def _dispatch_status_events(self) -> None:
        while self._status_events:
            kind, camera_id, at = self._status_events.popleft()
            if kind is _StatusKind.CONNECTED:
                self._status_listener.stream_connected(camera_id, at)
            elif kind is _StatusKind.LOST:
                self._status_listener.stream_lost(camera_id, at)
            elif kind is _StatusKind.RESTORED:
                self._status_listener.stream_restored(camera_id, at)
            else:
                self._status_listener.stream_degraded(camera_id, at)

    # ------------------------------------------------------------------
    # Shutdown
    # ------------------------------------------------------------------

    def close(self) -> None:
        """Stop every camera, join threads, dispatch remaining status."""
        if self._closed:
            return
        self._closed = True
        for camera_id in list(self._cameras):
            self._stop_camera(camera_id)
        # Status raised up to the join is still recorded; nothing after
        # close can arrive because every pump has stopped.
        self._dispatch_status_events()
