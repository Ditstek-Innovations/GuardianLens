"""RTSP integration — real cv2 against the dev simulator (TRD 13.2).

Runs only when the simulator is reachable:

    docker compose -f docker-compose.dev.yml --profile camera up -d
    # mediamtx serves rtsp://localhost:8554/cam1; the gl-rtsp-feed
    # container publishes an ffmpeg test pattern (~10 s to start).

The loss/restore test additionally stops and restarts the feed container
with the docker CLI, so it also requires docker and the named container.
Skipped otherwise; tear the profile down after running.
"""

from __future__ import annotations

import socket
import subprocess
import threading
import time
from datetime import datetime

import pytest

from guardian_lens_edge.rtsp import RtspSource
from guardian_lens_edge.unsealer import UnsealedStreamUrl

RTSP_HOST = "localhost"
RTSP_PORT = 8554
RTSP_URL = f"rtsp://{RTSP_HOST}:{RTSP_PORT}/cam1"
FEED_CONTAINER = "gl-rtsp-feed"

# Test-chosen value for the [OPEN] threshold, like every other [OPEN]
# parameter in this suite.
DECODE_FAILURE_THRESHOLD = 25


def sim_capture_factory(url: str):
    """cv2 capture tuned for the SIMULATOR, not for production.

    The sim's ffmpeg publishes H264 with libx264's default GOP (250
    frames = 25 s at 10 fps) and mediamtx delivers video to a new reader
    only from the next keyframe — so a reader joining mid-GOP legitimately
    waits up to ~25 s for its first frame. The production default read
    timeout (5 s, right for real cameras that send an IDR every 1–4 s)
    would abort that wait forever, so the test injects a 30 s read window
    through RtspSource's capture_factory seam.
    """
    import cv2

    return cv2.VideoCapture(
        url,
        cv2.CAP_FFMPEG,
        [
            cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, 10_000,
            cv2.CAP_PROP_READ_TIMEOUT_MSEC, 30_000,
        ],
    )


def _rtsp_port_open() -> bool:
    try:
        with socket.create_connection((RTSP_HOST, RTSP_PORT), timeout=1.0):
            return True
    except OSError:
        return False


def _docker_feed_running() -> bool:
    try:
        result = subprocess.run(
            [
                "docker", "inspect", "-f", "{{.State.Running}}",
                FEED_CONTAINER,
            ],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return False
    return result.returncode == 0 and result.stdout.strip() == "true"


pytestmark = pytest.mark.skipif(
    not _rtsp_port_open(),
    reason=(
        f"RTSP simulator not reachable on {RTSP_HOST}:{RTSP_PORT} — start "
        "it with: docker compose -f docker-compose.dev.yml --profile "
        "camera up -d"
    ),
)


class SignallingListener:
    def __init__(self) -> None:
        self.connected = threading.Event()
        self.lost = threading.Event()
        self.restored = threading.Event()
        self.events: list[tuple[str, str, datetime]] = []

    def stream_connected(self, camera_id: str, at: datetime) -> None:
        self.events.append(("connected", camera_id, at))
        self.connected.set()

    def stream_lost(self, camera_id: str, at: datetime) -> None:
        self.events.append(("lost", camera_id, at))
        self.lost.set()

    def stream_restored(self, camera_id: str, at: datetime) -> None:
        self.events.append(("restored", camera_id, at))
        self.restored.set()

    def stream_degraded(self, camera_id: str, at: datetime) -> None:
        self.events.append(("degraded", camera_id, at))


class Consumer:
    """Drains source.frames() on a background thread."""

    def __init__(self, source: RtspSource) -> None:
        self._source = source
        self.frames: list = []
        self.got_first = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True)

    def _run(self) -> None:
        for frame in self._source.frames():
            self.frames.append(frame)
            self.got_first.set()

    def start(self) -> "Consumer":
        self._thread.start()
        return self

    def stop(self, timeout: float = 15.0) -> None:
        self._source.stop()
        self._thread.join(timeout)


def test_rtsp_source_yields_real_jpeg_frames_at_the_sample_rate() -> None:
    listener = SignallingListener()
    source = RtspSource(
        "cam1",
        UnsealedStreamUrl(RTSP_URL),
        sample_rate_fps=2.0,
        decode_failure_threshold=DECODE_FAILURE_THRESHOLD,
        listener=listener,
        capture_factory=sim_capture_factory,
    )
    consumer = Consumer(source).start()
    try:
        # Up to ~25 s to the sim's next keyframe, then 2 s of sampling.
        deadline = time.monotonic() + 45
        while len(consumer.frames) < 4 and time.monotonic() < deadline:
            time.sleep(0.1)
    finally:
        consumer.stop(timeout=35.0)
    frames = list(consumer.frames)
    assert len(frames) >= 3, f"only {len(frames)} frames in 45s"
    assert listener.connected.is_set()
    for frame in frames:
        assert frame.camera_id == "cam1"
        assert frame.image_bytes is not None
        assert frame.image_bytes.startswith(b"\xff\xd8")  # real JPEG (SOI)
        assert frame.captured_at.tzinfo is not None
        assert RTSP_URL not in frame.image_ref
    # ~2 fps sampling: consecutive captures roughly 0.5 s apart.
    deltas = [
        (later.captured_at - earlier.captured_at).total_seconds()
        for earlier, later in zip(frames, frames[1:])
    ]
    average = sum(deltas) / len(deltas)
    assert 0.2 <= average <= 1.5, f"sampling cadence off: {deltas}"
    assert [frame.sequence for frame in frames[:3]] == [0, 1, 2]


@pytest.mark.skipif(
    not _docker_feed_running(),
    reason=f"docker container {FEED_CONTAINER} not running",
)
def test_stream_loss_fires_callback_and_restore_recovers() -> None:
    listener = SignallingListener()
    source = RtspSource(
        "cam1",
        UnsealedStreamUrl(RTSP_URL),
        sample_rate_fps=2.0,
        decode_failure_threshold=DECODE_FAILURE_THRESHOLD,
        listener=listener,
        capture_factory=sim_capture_factory,
    )
    consumer = Consumer(source).start()
    feed_stopped = False
    try:
        assert consumer.got_first.wait(45), "no frame before inducing loss"
        subprocess.run(
            ["docker", "stop", FEED_CONTAINER], check=True, timeout=30
        )
        feed_stopped = True
        # The loss surfaces within the sim factory's 30 s read window.
        assert listener.lost.wait(40), "stream_lost not reported"
        subprocess.run(
            ["docker", "start", FEED_CONTAINER], check=True, timeout=30
        )
        feed_stopped = False
        # Reconnect with backoff (1s, 2s, 4s …) while ffmpeg re-publishes;
        # worst case includes one full sim GOP before the first frame.
        assert listener.restored.wait(75), "stream_restored not reported"
    finally:
        consumer.stop(timeout=35.0)
        if feed_stopped:  # pragma: no cover - only on assertion failure
            subprocess.run(
                ["docker", "start", FEED_CONTAINER], check=False, timeout=30
            )
    kinds = [kind for kind, _, _ in listener.events]
    assert kinds.index("lost") < kinds.index("restored")
