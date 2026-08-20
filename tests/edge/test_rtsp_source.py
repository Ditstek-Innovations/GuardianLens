"""RtspSource unit tests — the MOD-1 failure-handling row, no cv2, no
wall clock.

A scripted FakeCapture stands in for cv2.VideoCapture; an injected
monotonic clock (advanced by the capture itself, one tick per grab) drives
the sampling cadence; an injected sleep records the backoff schedule; an
injected utc_now stamps captured_at deterministically.
"""

from __future__ import annotations

from collections import deque
from datetime import datetime, timedelta, timezone

import pytest

from guardian_lens_edge.rtsp import RtspSource
from guardian_lens_edge.unsealer import UnsealedStreamUrl

T0 = datetime(2026, 8, 13, 8, 0, 0, tzinfo=timezone.utc)
CAMERA_ID = "cam-lobby"
URL = UnsealedStreamUrl("rtsp://user:pw@camera.local/stream")

# Script vocabulary for one grab() call.
OK = "ok"            # grab True; retrieve returns the scripted image
DECODE_FAIL = "bad"  # grab True; retrieve returns (False, None)
LOST = "lost"        # grab False -> connection loss


class FakeClock:
    def __init__(self) -> None:
        self.now = 0.0

    def monotonic(self) -> float:
        return self.now

    def utc_now(self) -> datetime:
        return T0 + timedelta(seconds=self.now)

    def advance(self, seconds: float) -> None:
        self.now += seconds


class FakeCapture:
    """One connection's worth of scripted grab()/retrieve() behaviour."""

    def __init__(
        self,
        script: list[str],
        clock: FakeClock,
        *,
        opened: bool = True,
        seconds_per_grab: float = 0.1,
    ) -> None:
        self._script = deque(script)
        self._clock = clock
        self._opened = opened
        self._seconds_per_grab = seconds_per_grab
        self._current: str | None = None
        self.grab_calls = 0
        self.retrieve_calls = 0
        self.released = False

    def isOpened(self) -> bool:  # noqa: N802 - cv2 spelling
        return self._opened

    def grab(self) -> bool:
        self.grab_calls += 1
        self._clock.advance(self._seconds_per_grab)
        if not self._script:
            self._current = None
            return False  # script exhausted == stream ended
        self._current = self._script.popleft()
        if self._current == LOST:
            return False
        return True

    def retrieve(self) -> tuple[bool, object]:
        self.retrieve_calls += 1
        if self._current == OK:
            return True, f"image-{self.grab_calls}"
        return False, None

    def release(self) -> None:
        self.released = True


class RecordingListener:
    def __init__(self) -> None:
        self.events: list[tuple[str, str, datetime]] = []

    def kinds(self) -> list[str]:
        return [kind for kind, _, _ in self.events]

    def stream_connected(self, camera_id: str, at: datetime) -> None:
        self.events.append(("connected", camera_id, at))

    def stream_lost(self, camera_id: str, at: datetime) -> None:
        self.events.append(("lost", camera_id, at))

    def stream_restored(self, camera_id: str, at: datetime) -> None:
        self.events.append(("restored", camera_id, at))

    def stream_degraded(self, camera_id: str, at: datetime) -> None:
        self.events.append(("degraded", camera_id, at))


class Harness:
    """Wires RtspSource to scripted captures and recording collaborators."""

    def __init__(
        self,
        captures: list[FakeCapture],
        *,
        sample_rate_fps: float = 2.0,
        decode_failure_threshold: int = 2,
        stop_after_sleeps: int | None = None,
        jpeg_encoder=None,
    ) -> None:
        self.clock = FakeClock()
        self.listener = RecordingListener()
        self.sleeps: list[float] = []
        self.captures = deque(captures)
        self.opened_urls: list[str] = []
        self._stop_after_sleeps = stop_after_sleeps

        def capture_factory(url: str) -> FakeCapture:
            self.opened_urls.append(url)
            if not self.captures:
                raise AssertionError("capture factory script exhausted")
            return self.captures.popleft()

        def sleep(seconds: float) -> None:
            self.sleeps.append(seconds)
            self.clock.advance(seconds)
            if (
                self._stop_after_sleeps is not None
                and len(self.sleeps) >= self._stop_after_sleeps
            ):
                self.source.stop()

        self.source = RtspSource(
            CAMERA_ID,
            URL,
            sample_rate_fps=sample_rate_fps,
            decode_failure_threshold=decode_failure_threshold,
            listener=self.listener,
            capture_factory=capture_factory,
            jpeg_encoder=jpeg_encoder
            or (lambda image: f"jpeg:{image}".encode()),
            monotonic=self.clock.monotonic,
            utc_now=self.clock.utc_now,
            sleep=sleep,
        )

    def collect(self, max_frames: int) -> list:
        frames = []
        for frame in self.source.frames():
            frames.append(frame)
            if len(frames) >= max_frames:
                self.source.stop()
        return frames


# ---------------------------------------------------------------------------
# Sampling cadence: grab drains continuously, retrieve only at instants
# ---------------------------------------------------------------------------


def test_sampling_grabs_continuously_but_retrieves_at_sample_rate() -> None:
    # Native stream ~10 fps (0.1s per grab); sampling at 2 fps (0.5s).
    capture = FakeCapture([OK] * 20, None, seconds_per_grab=0.1)
    after = FakeCapture([], None, opened=False)  # ends the run via backoff
    harness = Harness(
        [capture, after], sample_rate_fps=2.0, stop_after_sleeps=1
    )
    capture._clock = harness.clock  # clock exists only after harness init
    after._clock = harness.clock
    frames = harness.collect(max_frames=10)
    # Samples land at t=0.1, 0.6, 1.1, 1.6 — every 5th grab; the driver
    # buffer was drained by all 20 scripted grabs (plus the end-of-script
    # grab) but only 4 decodes happened.
    assert len(frames) == 4
    assert capture.grab_calls == 21
    assert capture.retrieve_calls == 4
    assert [frame.sequence for frame in frames] == [0, 1, 2, 3]
    # ADR-007: captured_at is the edge clock at retrieve time — the first
    # sample lands on the first grab, subsequent ones one interval apart
    # (float accumulation may shift an instant onto the next grab).
    captured = [frame.captured_at for frame in frames]
    assert captured[0] == T0 + timedelta(seconds=0.1)
    deltas = [
        (later - earlier).total_seconds()
        for earlier, later in zip(captured, captured[1:])
    ]
    assert all(0.4 <= delta <= 0.7 for delta in deltas), deltas
    assert all(frame.camera_id == CAMERA_ID for frame in frames)


def test_frames_carry_jpeg_bytes_in_memory_and_a_non_url_ref() -> None:
    capture = FakeCapture([OK] * 5, None, seconds_per_grab=0.5)
    harness = Harness([capture], stop_after_sleeps=1)
    capture._clock = harness.clock
    frames = harness.collect(max_frames=3)
    assert [frame.image_bytes for frame in frames] == [
        b"jpeg:image-1",
        b"jpeg:image-2",
        b"jpeg:image-3",
    ]
    for frame in frames:
        # The image_ref must never leak the stream URL (credential).
        assert "rtsp://" not in frame.image_ref.replace(
            f"rtsp:{CAMERA_ID}", ""
        )
        assert frame.image_ref == f"rtsp:{CAMERA_ID}:{frame.sequence}"


# ---------------------------------------------------------------------------
# Connection loss: backoff schedule, unlimited retries, gap callbacks
# ---------------------------------------------------------------------------


def test_backoff_schedule_is_exponential_and_capped_at_60() -> None:
    # Eight consecutive failed opens, then stopped by the sleep counter.
    failed = [FakeCapture([], None, opened=False) for _ in range(8)]
    harness = Harness(failed, stop_after_sleeps=8)
    for capture in failed:
        capture._clock = harness.clock
    frames = harness.collect(max_frames=1)
    assert frames == []
    assert harness.sleeps == [1.0, 2.0, 4.0, 8.0, 16.0, 32.0, 60.0, 60.0]
    # Loss was reported exactly once for the whole outage.
    assert harness.listener.kinds() == ["lost"]
    assert all(capture.released for capture in failed)


def test_loss_mid_stream_reports_lost_then_restored_on_reconnect() -> None:
    streaming = FakeCapture([OK, OK, LOST], None, seconds_per_grab=0.5)
    reconnect_fail = FakeCapture([], None, opened=False)
    recovered = FakeCapture([OK, OK], None, seconds_per_grab=0.5)
    harness = Harness([streaming, reconnect_fail, recovered])
    for capture in (streaming, reconnect_fail, recovered):
        capture._clock = harness.clock
    frames = harness.collect(max_frames=3)
    assert len(frames) == 3
    # connected (first open) -> lost (grab failed; one failed reopen keeps
    # the same outage) -> restored (successful reconnect).
    assert harness.listener.kinds() == ["connected", "lost", "restored"]
    assert harness.sleeps == [1.0]  # backoff restarted at 1s for the outage
    assert streaming.released and reconnect_fail.released
    # Sequences continue across the reconnect: same camera, one stream.
    assert [frame.sequence for frame in frames] == [0, 1, 2]


def test_never_connected_camera_still_reports_lost_once() -> None:
    # RS-5: a camera that never connects is unwatched — recorded, never
    # inferred. One lost event, no restored.
    failed = [FakeCapture([], None, opened=False) for _ in range(3)]
    harness = Harness(failed, stop_after_sleeps=3)
    for capture in failed:
        capture._clock = harness.clock
    harness.collect(max_frames=1)
    assert harness.listener.kinds() == ["lost"]


def test_backoff_resets_only_when_frames_flow_again() -> None:
    first = FakeCapture([LOST], None)  # opens, delivers nothing
    fail_a = FakeCapture([], None, opened=False)
    second = FakeCapture([OK, LOST], None, seconds_per_grab=0.5)
    fail_b = FakeCapture([], None, opened=False)
    third = FakeCapture([OK], None, seconds_per_grab=0.5)
    captures = [first, fail_a, second, fail_b, third]
    harness = Harness(captures)
    for capture in captures:
        capture._clock = harness.clock
    harness.collect(max_frames=2)
    # One outage spans open-but-frameless connections (1s then 2s); once
    # frames flowed on `second`, the next outage starts at 1s again.
    assert harness.sleeps == [1.0, 2.0, 1.0]
    assert harness.listener.kinds() == [
        "lost",
        "restored",
        "lost",
        "restored",
    ]


def test_server_that_accepts_sessions_but_sends_no_frames_backs_off() -> None:
    # Regression: mediamtx (and some cameras) accept the RTSP session with
    # no publisher behind it. That must count as the SAME outage — growing
    # backoff, no spurious connected/restored churn.
    frameless = [FakeCapture([LOST], None) for _ in range(4)]
    harness = Harness(frameless, stop_after_sleeps=4)
    for capture in frameless:
        capture._clock = harness.clock
    frames = harness.collect(max_frames=1)
    assert frames == []
    assert harness.sleeps == [1.0, 2.0, 4.0, 8.0]
    assert harness.listener.kinds() == ["lost"]


# ---------------------------------------------------------------------------
# Decode errors: drop + count + continue; sustained -> degraded
# ---------------------------------------------------------------------------


def test_single_decode_error_drops_counts_and_continues() -> None:
    capture = FakeCapture([OK, DECODE_FAIL, OK], None, seconds_per_grab=0.5)
    harness = Harness([capture], stop_after_sleeps=1)
    capture._clock = harness.clock
    frames = harness.collect(max_frames=2)
    assert len(frames) == 2
    assert harness.source.decode_errors_total == 1
    assert "degraded" not in harness.listener.kinds()


def test_encoder_failure_counts_as_decode_error() -> None:
    def broken_encoder(image: object) -> bytes:
        raise ValueError("boom")

    capture = FakeCapture([OK, OK], None, seconds_per_grab=0.5)
    after = FakeCapture([], None, opened=False)
    harness = Harness(
        [capture, after],
        decode_failure_threshold=5,
        stop_after_sleeps=1,
        jpeg_encoder=broken_encoder,
    )
    capture._clock = harness.clock
    after._clock = harness.clock
    frames = harness.collect(max_frames=1)
    assert frames == []
    assert harness.source.decode_errors_total == 2


def test_sustained_decode_failure_over_threshold_reports_degraded() -> None:
    script = [DECODE_FAIL] * 4 + [OK]
    capture = FakeCapture(script, None, seconds_per_grab=0.5)
    harness = Harness(
        [capture], decode_failure_threshold=2, stop_after_sleeps=1
    )
    capture._clock = harness.clock
    frames = harness.collect(max_frames=1)
    assert len(frames) == 1  # the stream continued and recovered
    assert harness.source.decode_errors_total == 4
    # Degraded fired exactly once per streak, at failure #3 (> threshold 2).
    assert harness.listener.kinds() == ["connected", "degraded"]


def test_degraded_rearms_after_recovery() -> None:
    script = [DECODE_FAIL] * 3 + [OK] + [DECODE_FAIL] * 3 + [OK]
    capture = FakeCapture(script, None, seconds_per_grab=0.5)
    harness = Harness(
        [capture], decode_failure_threshold=2, stop_after_sleeps=1
    )
    capture._clock = harness.clock
    harness.collect(max_frames=2)
    assert harness.listener.kinds() == [
        "connected",
        "degraded",
        "degraded",
    ]
    assert harness.source.decode_errors_total == 6


# ---------------------------------------------------------------------------
# Construction and shutdown
# ---------------------------------------------------------------------------


def test_decode_failure_threshold_is_required_and_validated() -> None:
    listener = RecordingListener()
    with pytest.raises(TypeError):
        # [OPEN] — no default exists to fall back to.
        RtspSource(CAMERA_ID, URL, sample_rate_fps=2.0, listener=listener)
    with pytest.raises(ValueError):
        RtspSource(
            CAMERA_ID,
            URL,
            sample_rate_fps=2.0,
            decode_failure_threshold=0,
            listener=listener,
        )
    with pytest.raises(ValueError):
        RtspSource(
            CAMERA_ID,
            URL,
            sample_rate_fps=0.0,
            decode_failure_threshold=2,
            listener=listener,
        )


def test_stop_interrupts_streaming_and_releases_the_capture() -> None:
    capture = FakeCapture([OK] * 100, None, seconds_per_grab=0.5)
    harness = Harness([capture])
    capture._clock = harness.clock
    frames = harness.collect(max_frames=2)  # collect() stops the source
    assert len(frames) == 2
    assert harness.source.stopped
    assert capture.released
    assert capture.grab_calls < 100  # it did not run the script out


def test_redacted_rtsp_target_omits_userinfo() -> None:
    from guardian_lens_edge.rtsp import redacted_rtsp_target

    shown = redacted_rtsp_target("rtsp://user:secret@192.168.0.20:554/stream1")
    assert "secret" not in shown
    assert "user" not in shown
    assert "192.168.0.20:554/stream1" in shown
    assert "with camera login" in shown


def test_redacted_rtsp_target_flags_missing_host() -> None:
    from guardian_lens_edge.rtsp import redacted_rtsp_target

    shown = redacted_rtsp_target("rtsp:192.168.0.20")
    assert "missing host" in shown
    assert "secret" not in shown


def test_diagnose_maps_401_without_echoing_url() -> None:
    from guardian_lens_edge import rtsp as rtsp_mod

    class _Result:
        stderr = "rtsp://user:pw@cam/stream1: Server returned 401 Unauthorized"
        stdout = ""

    def fake_run(*_args, **_kwargs):
        return _Result()

    monkey = pytest.MonkeyPatch()
    monkey.setattr(rtsp_mod.subprocess, "run", fake_run)
    try:
        reason = rtsp_mod.diagnose_rtsp_open_failure(
            "rtsp://user:pw@cam/stream1"
        )
    finally:
        monkey.undo()
    assert "401" in reason
    assert "pw" not in reason
    assert "user" not in reason


def test_connect_failure_log_names_host_not_password(caplog) -> None:
    failed = FakeCapture([], None, opened=False)
    harness = Harness(
        [failed],
        stop_after_sleeps=1,
    )
    harness.source._open_diagnoser = lambda _url: "camera returned 401 Unauthorized"
    failed._clock = harness.clock
    with caplog.at_level("WARNING"):
        harness.collect(max_frames=1)
    text = "\n".join(record.getMessage() for record in caplog.records)
    assert "pw" not in text
    assert "camera.local" in text
    assert "401" in text
