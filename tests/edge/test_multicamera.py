"""MultiCameraSource wiring — threads, bounded queue, config rebuild, and
StreamGapRouter routing into the existing gap mechanics. No cv2: fake
per-camera sources are injected through the source factory.
"""

from __future__ import annotations

import base64
import threading
import time
from datetime import datetime, timedelta, timezone

import pytest

from guardian_lens_edge.config import AgentConfig, CameraConfig
from guardian_lens_edge.frames import Frame
from guardian_lens_edge.multicamera import (
    CameraStreamSpec,
    MultiCameraSource,
    StreamGapRouter,
)
from guardian_lens_edge.state import STREAM_LOST_REASON, GapRecorder
from guardian_lens_edge.store import EdgeStore
from guardian_lens_edge.unsealer import CredentialUnsealer

from tests.edge.conftest import SITE_ID

T0 = datetime(2026, 8, 13, 9, 0, 0, tzinfo=timezone.utc)
KEY = bytes.fromhex("cc" * 32)
KEY_ID = "edge-key-1"
WAIT_SECONDS = 5.0


def seal(url: str, key: bytes = KEY) -> str:
    """Seal in the control plane's exact format (mirrored, not imported:
    the format contract lives in test_unsealer.py's round-trip)."""
    import os

    from cryptography.hazmat.primitives.ciphers.aead import AESGCM

    nonce = os.urandom(12)
    ciphertext = AESGCM(key).encrypt(nonce, url.encode(), None)
    return base64.b64encode(nonce + ciphertext).decode()


def camera(
    camera_id: str,
    url: str | None = "rtsp://cam.local/s1",
    *,
    fps: float = 2.0,
    key_id: str = KEY_ID,
) -> CameraConfig:
    return CameraConfig(
        camera_id=camera_id,
        name=f"Camera {camera_id}",
        sample_rate_fps=fps,
        stream_url_sealed=seal(url) if url is not None else None,
        stream_url_key_id=key_id if url is not None else None,
    )


def config(*cameras: CameraConfig, version: int = 1) -> AgentConfig:
    return AgentConfig(
        config_version=version, site_id=SITE_ID, cameras=list(cameras)
    )


def make_frame(camera_id: str, sequence: int) -> Frame:
    return Frame(
        camera_id=camera_id,
        captured_at=T0 + timedelta(seconds=sequence),
        image_ref=f"rtsp:{camera_id}:{sequence}",
        sequence=sequence,
        image_bytes=b"\xff\xd8fake",
    )


class ScriptedSource:
    """Fake per-camera source: yields scripted frames, then parks until
    stopped. Records the unsealed URL it was composed with."""

    def __init__(self, spec, stream_url, listener) -> None:
        self.spec = spec
        self.stream_url = stream_url
        self.listener = listener
        self.frames_to_yield: list[Frame] = []
        self.started = threading.Event()
        self._stop = threading.Event()

    def frames(self):
        self.started.set()
        for frame in self.frames_to_yield:
            if self._stop.is_set():
                return
            yield frame
        self._stop.wait()

    def stop(self) -> None:
        self._stop.set()

    @property
    def stopped(self) -> bool:
        return self._stop.is_set()


class RecordingStatus:
    def __init__(self) -> None:
        self.events: list[tuple[str, str]] = []

    def kinds(self) -> list[tuple[str, str]]:
        return list(self.events)

    def stream_connected(self, camera_id: str, at) -> None:
        self.events.append(("connected", camera_id))

    def stream_lost(self, camera_id: str, at) -> None:
        self.events.append(("lost", camera_id))

    def stream_restored(self, camera_id: str, at) -> None:
        self.events.append(("restored", camera_id))

    def stream_degraded(self, camera_id: str, at) -> None:
        self.events.append(("degraded", camera_id))


class Wiring:
    def __init__(self, *, queue_capacity: int = 8) -> None:
        self.status = RecordingStatus()
        self.built: list[ScriptedSource] = []
        self.scripts: dict[str, list[Frame]] = {}
        self.source = MultiCameraSource(
            unsealer=CredentialUnsealer(KEY, KEY_ID),
            status_listener=self.status,
            decode_failure_threshold=3,
            queue_capacity=queue_capacity,
            source_factory=self._factory,
        )

    def _factory(self, spec, stream_url, listener) -> ScriptedSource:
        scripted = ScriptedSource(spec, stream_url, listener)
        scripted.frames_to_yield = self.scripts.get(spec.camera_id, [])
        self.built.append(scripted)
        return scripted

    def source_for(self, camera_id: str) -> ScriptedSource:
        for scripted in reversed(self.built):
            if scripted.spec.camera_id == camera_id:
                return scripted
        raise AssertionError(f"no source built for {camera_id}")


def wait_until(predicate, timeout: float = WAIT_SECONDS) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return
        time.sleep(0.01)
    raise AssertionError("condition not reached in time")


# ---------------------------------------------------------------------------
# Composition and unsealing
# ---------------------------------------------------------------------------


def test_apply_config_starts_one_source_per_camera_with_unsealed_url() -> None:
    wiring = Wiring()
    url_a = "rtsp://user:pw@cam-a.local/s1"
    url_b = "rtsp://user:pw@cam-b.local/s1"
    wiring.source.apply_config(
        config(
            camera("cam-a", url_a),
            camera("cam-b", url_b, fps=4.0),
        ),
        T0,
    )
    try:
        assert wiring.source.running_camera_ids == ["cam-a", "cam-b"]
        assert wiring.source_for("cam-a").stream_url.reveal() == url_a
        assert wiring.source_for("cam-b").stream_url.reveal() == url_b
        assert wiring.source_for("cam-b").spec.sample_rate_fps == 4.0
    finally:
        wiring.source.close()


def test_frames_from_camera_threads_arrive_on_the_queue() -> None:
    wiring = Wiring()
    wiring.scripts["cam-a"] = [make_frame("cam-a", 0), make_frame("cam-a", 1)]
    wiring.source.apply_config(config(camera("cam-a")), T0)
    try:
        received = []
        for _ in range(2):
            frame = wiring.source.next_frame(timeout=WAIT_SECONDS)
            assert frame is not None
            received.append(frame)
        assert [frame.sequence for frame in received] == [0, 1]
        assert received[0].image_bytes == b"\xff\xd8fake"
    finally:
        wiring.source.close()


def test_unsealable_credential_skips_camera_and_opens_gap_report() -> None:
    wiring = Wiring()
    bad = CameraConfig(
        camera_id="cam-bad",
        name="Bad key id",
        sample_rate_fps=2.0,
        stream_url_sealed=seal("rtsp://cam.local/s1"),
        stream_url_key_id="rotated-away-key",
    )
    wiring.source.apply_config(config(bad, camera("cam-good")), T0)
    try:
        # The failed camera is not running; the good one is.
        assert wiring.source.running_camera_ids == ["cam-good"]
        assert ("lost", "cam-bad") in wiring.status.kinds()
    finally:
        wiring.source.close()


def test_placeholder_sealed_credential_is_reported_not_started() -> None:
    wiring = Wiring()
    placeholder = CameraConfig(
        camera_id="cam-dev",
        name="Placeholder sealed",
        sample_rate_fps=2.0,
        stream_url_sealed=base64.b64encode(
            b"gl-dev-sealed:v1:" + b"\x00" * 48
        ).decode(),
        stream_url_key_id=KEY_ID,
    )
    wiring.source.apply_config(config(placeholder), T0)
    try:
        assert wiring.source.running_camera_ids == []
        assert wiring.status.kinds() == [("lost", "cam-dev")]
    finally:
        wiring.source.close()


def test_camera_without_sealed_url_is_reported_not_started() -> None:
    wiring = Wiring()
    wiring.source.apply_config(config(camera("cam-nourl", None)), T0)
    try:
        assert wiring.source.running_camera_ids == []
        assert wiring.status.kinds() == [("lost", "cam-nourl")]
    finally:
        wiring.source.close()


# ---------------------------------------------------------------------------
# Backpressure: bounded queue drops stale frames and keeps the newest
# ---------------------------------------------------------------------------


def test_full_queue_drops_oldest_sample_and_keeps_latest() -> None:
    wiring = Wiring(queue_capacity=2)
    wiring.scripts["cam-a"] = [make_frame("cam-a", n) for n in range(5)]
    wiring.source.apply_config(config(camera("cam-a")), T0)
    try:
        # The pump never blocks: it finishes all 5 puts without the
        # consumer taking anything; 3 stale samples are dropped.
        wait_until(
            lambda: wiring.source.dropped_frames().get("cam-a") == 3
        )
        # The queue keeps the freshest samples so live view and detection
        # do not replay an ever-growing backlog.
        first = wiring.source.next_frame(timeout=WAIT_SECONDS)
        second = wiring.source.next_frame(timeout=WAIT_SECONDS)
        assert (first.sequence, second.sequence) == (3, 4)
        assert wiring.source.next_frame(timeout=0.05) is None
    finally:
        wiring.source.close()


# ---------------------------------------------------------------------------
# Config changes rebuild only what changed
# ---------------------------------------------------------------------------


def test_config_change_rebuilds_added_removed_and_changed_cameras() -> None:
    wiring = Wiring()
    cam_a = camera("cam-a")
    cam_b = camera("cam-b")
    wiring.source.apply_config(config(cam_a, cam_b), T0)
    source_a = wiring.source_for("cam-a")
    source_b = wiring.source_for("cam-b")
    wait_until(lambda: source_a.started.is_set() and source_b.started.is_set())

    # v2: cam-a unchanged, cam-b sample rate changed, cam-c added.
    cam_b_faster = camera("cam-b", fps=8.0)
    wiring.source.apply_config(
        config(cam_a, cam_b_faster, camera("cam-c"), version=2), T0
    )
    try:
        assert wiring.source.running_camera_ids == [
            "cam-a",
            "cam-b",
            "cam-c",
        ]
        # Unchanged camera kept its source; changed camera got a new one.
        assert wiring.source_for("cam-a") is source_a
        assert not source_a.stopped
        assert source_b.stopped
        assert wiring.source_for("cam-b") is not source_b
        assert wiring.source_for("cam-b").spec.sample_rate_fps == 8.0

        # v3: cam-a removed.
        wiring.source.apply_config(
            config(cam_b_faster, camera("cam-c"), version=3), T0
        )
        assert wiring.source.running_camera_ids == ["cam-b", "cam-c"]
        assert source_a.stopped
    finally:
        wiring.source.close()


def test_close_stops_every_camera_thread() -> None:
    wiring = Wiring()
    wiring.source.apply_config(config(camera("cam-a"), camera("cam-b")), T0)
    source_a = wiring.source_for("cam-a")
    source_b = wiring.source_for("cam-b")
    wiring.source.close()
    assert source_a.stopped and source_b.stopped
    assert wiring.source.running_camera_ids == []


# ---------------------------------------------------------------------------
# Status events reach the listener on the consumer thread
# ---------------------------------------------------------------------------


def test_camera_thread_status_is_dispatched_on_the_consumer_thread() -> None:
    wiring = Wiring()
    dispatch_threads: list[str] = []

    class ThreadAwareStatus(RecordingStatus):
        def stream_lost(self, camera_id: str, at) -> None:
            dispatch_threads.append(threading.current_thread().name)
            super().stream_lost(camera_id, at)

    wiring.source._status_listener = ThreadAwareStatus()  # noqa: SLF001

    class LossySource(ScriptedSource):
        def frames(self):
            self.listener.stream_lost(self.spec.camera_id, T0)
            self.started.set()
            self._stop.wait()
            return iter(())

    def lossy_factory(spec, url, listener) -> LossySource:
        scripted = LossySource(spec, url, listener)
        wiring.built.append(scripted)
        return scripted

    wiring.source._source_factory = lossy_factory  # noqa: SLF001
    wiring.source.apply_config(config(camera("cam-a")), T0)
    try:
        wait_until(lambda: wiring.source_for("cam-a").started.is_set())
        assert dispatch_threads == []  # nothing dispatched from the pump
        wiring.source.next_frame(timeout=0.05)
        assert dispatch_threads == [threading.main_thread().name]
    finally:
        wiring.source.close()


# ---------------------------------------------------------------------------
# StreamGapRouter → the EXISTING gap mechanics (RS-5)
# ---------------------------------------------------------------------------


def test_router_opens_stream_lost_gap_and_closes_on_restore(
    store: EdgeStore,
) -> None:
    router = StreamGapRouter(GapRecorder(store))
    router.stream_lost("cam-a", T0)
    gaps = store.open_gaps()
    assert len(gaps) == 1
    assert gaps[0].camera_id == "cam-a"
    assert gaps[0].reason == STREAM_LOST_REASON
    # The open was enqueued to the outbox with ended_at null.
    batch = store.claim_batch(10, now="2026-08-13T09:00:00+00:00")
    assert [row.kind for row in batch] == ["coverage_gap"]
    assert batch[0].payload["reason"] == STREAM_LOST_REASON
    assert batch[0].payload["ended_at"] is None

    router.stream_restored("cam-a", T0 + timedelta(seconds=42))
    assert store.open_gaps() == []
    batch = store.claim_batch(10, now="2026-08-13T09:01:00+00:00")
    assert len(batch) == 1
    closed = batch[0].payload
    assert closed["id"] == gaps[0].gap_id  # same gap id — idempotent upsert
    assert closed["ended_at"] is not None


def test_router_does_not_duplicate_an_open_gap(store: EdgeStore) -> None:
    router = StreamGapRouter(GapRecorder(store))
    router.stream_lost("cam-a", T0)
    router.stream_lost("cam-a", T0 + timedelta(seconds=5))
    assert len(store.open_gaps()) == 1


def test_router_scopes_gaps_per_camera(store: EdgeStore) -> None:
    router = StreamGapRouter(GapRecorder(store))
    router.stream_lost("cam-a", T0)
    router.stream_lost("cam-b", T0)
    router.stream_restored("cam-a", T0 + timedelta(seconds=1))
    remaining = store.open_gaps()
    assert [gap.camera_id for gap in remaining] == ["cam-b"]


def test_router_connected_closes_composition_failure_gap(
    store: EdgeStore,
) -> None:
    # A camera that could not be composed (unsealable credential) opened a
    # gap; when a later config change starts it and it CONNECTS, the gap
    # closes even though no loss/restore cycle happened inside the source.
    router = StreamGapRouter(GapRecorder(store))
    router.stream_lost("cam-a", T0)
    assert len(store.open_gaps()) == 1
    router.stream_connected("cam-a", T0 + timedelta(seconds=30))
    assert store.open_gaps() == []


def test_router_degraded_is_an_alert_not_a_gap(
    store: EdgeStore, caplog: pytest.LogCaptureFixture
) -> None:
    router = StreamGapRouter(GapRecorder(store))
    with caplog.at_level("ERROR", logger="guardian_lens_edge.multicamera"):
        router.stream_degraded("cam-a", T0)
    assert store.open_gaps() == []  # stream is up; nothing is unwatched
    assert any("DEGRADED" in record.message for record in caplog.records)


# ---------------------------------------------------------------------------
# Spec equality drives rebuilds
# ---------------------------------------------------------------------------


def test_spec_equality_is_by_value() -> None:
    sealed = seal("rtsp://cam.local/s1")
    left = CameraStreamSpec("cam-a", 2.0, sealed, KEY_ID)
    right = CameraStreamSpec("cam-a", 2.0, sealed, KEY_ID)
    assert left == right
    assert left != CameraStreamSpec("cam-a", 4.0, sealed, KEY_ID)
