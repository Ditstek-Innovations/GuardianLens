"""run_live — the rtsp-mode wall-clock loop, driven deterministically with
an injected clock and a fake live source. Also the NullDetector default
and the evidence-bytes path for live frames.
"""

from __future__ import annotations

import threading
from collections import deque
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from guardian_lens_edge.agent import EdgeAgent
from guardian_lens_edge.auth import AgentAuthenticator
from guardian_lens_edge.config_sync import ConfigSync
from guardian_lens_edge.detector import Detection, NullDetector
from guardian_lens_edge.events import EventBuilder
from guardian_lens_edge.frames import Frame, SyntheticSource
from guardian_lens_edge.publisher import Publisher
from guardian_lens_edge.rules import RuleEvaluator
from guardian_lens_edge.scenario import Scenario
from guardian_lens_edge.state import AgentStateMachine
from guardian_lens_edge.store import EdgeStore

from tests.edge.conftest import (
    AGENT_ID,
    CAMERA_ID,
    SITE_ID,
    FakeControlPlane,
    make_config,
)

API = "http://control-plane.test"
T0 = datetime(2026, 8, 13, 10, 0, 0, tzinfo=timezone.utc)


class SteppingClock:
    """utc_now() that advances a fixed step per call — the loop's pace."""

    def __init__(self, step_seconds: float = 0.5) -> None:
        self.now = T0
        self.step = timedelta(seconds=step_seconds)
        self.calls = 0

    def __call__(self) -> datetime:
        current = self.now
        self.now = self.now + self.step
        self.calls += 1
        return current


class FakeLiveSource:
    """LiveFrameSource double: hands out scripted frames, records calls,
    and stops the loop when its script is exhausted."""

    def __init__(
        self, frames: list[Frame], stop_event: threading.Event,
        extra_polls: int = 6,
    ) -> None:
        self._frames = deque(frames)
        self._stop_event = stop_event
        self._extra_polls = extra_polls
        self.applied: list = []
        self.closed = False

    def next_frame(self, timeout: float) -> Frame | None:
        if self._frames:
            return self._frames.popleft()
        self._extra_polls -= 1
        if self._extra_polls <= 0:
            self._stop_event.set()
        return None

    def apply_config(self, config, now) -> None:
        self.applied.append(config)

    def close(self) -> None:
        self.closed = True


def live_frame(sequence: int, seconds: float) -> Frame:
    return Frame(
        camera_id=CAMERA_ID,
        captured_at=T0 + timedelta(seconds=seconds),
        image_ref=f"rtsp:{CAMERA_ID}:{sequence}",
        sequence=sequence,
        image_bytes=b"\xff\xd8\xff\xe0live-jpeg-bytes",
    )


def build_live_agent(
    tmp_path: Path,
    plane: FakeControlPlane,
    frame_source,
    detector,
) -> tuple[EdgeAgent, EdgeStore]:
    store = EdgeStore(
        tmp_path / "edge.sqlite3",
        warning_bytes=1_000_000,
        critical_bytes=2_000_000,
    )
    client = plane.client()
    auth = AgentAuthenticator(client, API, "site:agent:secret")
    agent = EdgeAgent(
        store=store,
        frame_source=frame_source,
        detector=detector,
        evaluator=RuleEvaluator(store),
        builder=EventBuilder(store, tmp_path / "spool", AGENT_ID),
        publisher=Publisher(store, client, API, auth),
        config_sync=ConfigSync(store, client, API, AGENT_ID, auth),
        state=AgentStateMachine(
            store,
            failure_window=8,
            degraded_failure_rate=0.5,
            halt_failure_rate=0.75,
        ),
        agent_id=AGENT_ID,
        site_id=SITE_ID,
    )
    return agent, store


def config_document(version: int = 1) -> dict:
    document = make_config(config_version=version).model_dump()
    return document


def test_run_live_processes_frames_ticks_and_shuts_down_cleanly(
    tmp_path: Path,
) -> None:
    plane = FakeControlPlane(config_document())
    stop_event = threading.Event()
    source = FakeLiveSource(
        [live_frame(0, 0.0), live_frame(1, 0.5)], stop_event
    )
    detector = NullDetector()
    agent, store = build_live_agent(tmp_path, plane, source, detector)
    clock = SteppingClock(step_seconds=0.5)
    try:
        agent.run_live(
            stop_event=stop_event,
            publish_interval_seconds=1.0,
            config_interval_seconds=2.0,
            health_interval_seconds=2.0,
            frame_timeout_seconds=0.0,
            utc_now=clock,
        )
        # The two live frames went through process_frame -> NullDetector.
        assert detector.frames_seen == 2
        # Configuration was fetched and applied to the source at startup.
        assert len(source.applied) == 1
        assert source.applied[0].config_version == 1
        # Clean shutdown: source closed, outbox drained by the final tick.
        assert source.closed
        assert store.pending_count() == 0
        # Health beats reached the control plane through the outbox.
        assert len(plane.received_health) >= 1
        assert plane.received_health[0]["applied_config_version"] == 1
    finally:
        store.close()


def test_run_live_rebuilds_sources_when_config_version_changes(
    tmp_path: Path,
) -> None:
    plane = FakeControlPlane(config_document(version=1))
    # Second config fetch returns version 2.
    plane.config_responses = [
        config_document(version=1),
        config_document(version=2),
        config_document(version=2),
        config_document(version=2),
    ]
    stop_event = threading.Event()
    source = FakeLiveSource([], stop_event, extra_polls=10)
    agent, store = build_live_agent(
        tmp_path, plane, source, NullDetector()
    )
    # Big steps so the config interval elapses on every loop iteration.
    clock = SteppingClock(step_seconds=5.0)
    try:
        agent.run_live(
            stop_event=stop_event,
            publish_interval_seconds=1.0,
            config_interval_seconds=4.0,
            health_interval_seconds=1000.0,
            frame_timeout_seconds=0.0,
            utc_now=clock,
        )
        versions = [config.config_version for config in source.applied]
        assert versions[0] == 1  # initial composition
        assert 2 in versions  # rebuild on version change
        # No rebuild without a version change: applied once per version.
        assert versions.count(2) == 1
    finally:
        store.close()


def test_run_live_requires_a_live_frame_source(tmp_path: Path) -> None:
    plane = FakeControlPlane(config_document())
    scenario = Scenario.from_list([])
    agent, store = build_live_agent(
        tmp_path,
        plane,
        SyntheticSource(scenario, start_at=T0),
        NullDetector(),
    )
    try:
        with pytest.raises(TypeError, match="live frame source"):
            agent.run_live(stop_event=threading.Event())
    finally:
        store.close()


def test_null_detector_counts_frames_and_never_detects() -> None:
    detector = NullDetector()
    assert detector.model_version is None
    for sequence in range(3):
        assert detector.detect(live_frame(sequence, float(sequence))) == []
    assert detector.frames_seen == 3


def test_live_frame_bytes_become_the_event_evidence(tmp_path: Path) -> None:
    """The rtsp evidence path: in-memory JPEG bytes reach the spool only
    when a candidate is admitted, and verbatim."""

    class OneShotDetector:
        model_version = "test-model-1.0.0"

        def detect(self, frame: Frame) -> list[Detection]:
            return [
                Detection(
                    class_name="person_without_helmet",
                    bbox_norm=(0.4, 0.4, 0.6, 0.85),
                    confidence=0.9,
                )
            ]

    plane = FakeControlPlane(config_document())
    stop_event = threading.Event()
    source = FakeLiveSource([live_frame(0, 0.0)], stop_event)
    agent, store = build_live_agent(
        tmp_path, plane, source, OneShotDetector()
    )
    try:
        agent.run_live(
            stop_event=stop_event,
            publish_interval_seconds=1000.0,  # keep the event in the outbox
            config_interval_seconds=1000.0,
            health_interval_seconds=1000.0,
            frame_timeout_seconds=0.0,
            utc_now=SteppingClock(step_seconds=0.5),
        )
    finally:
        # The final drain published it; inspect what the plane received.
        store.close()
    assert len(plane.received_events) == 1
    event = plane.received_events[0]
    assert event["camera_id"] == CAMERA_ID
    assert event["model_version"] == "test-model-1.0.0"
    import base64

    evidence = base64.b64decode(event["evidence"]["data_b64"])
    assert evidence == b"\xff\xd8\xff\xe0live-jpeg-bytes"
