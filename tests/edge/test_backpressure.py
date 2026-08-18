"""Backpressure — DATABASE.md 11.4 / RS-2: the disk cap halts detection,
opens a gap, and recovery closes it and resumes. Never drops an event."""

from __future__ import annotations

from pathlib import Path
from typing import Iterator

import pytest

from guardian_lens_edge.agent import EdgeAgent
from guardian_lens_edge.auth import AgentAuthenticator
from guardian_lens_edge.config_sync import ConfigSync
from guardian_lens_edge.detector import SyntheticDetector
from guardian_lens_edge.events import EventBuilder
from guardian_lens_edge.frames import SyntheticSource
from guardian_lens_edge.publisher import Publisher
from guardian_lens_edge.rules import RuleEvaluator
from guardian_lens_edge.scenario import Scenario
from guardian_lens_edge.state import AgentStateMachine, HaltReason, OperatingState
from guardian_lens_edge.store import EdgeStore

from tests.edge.conftest import (
    AGENT_ID,
    CAMERA_ID,
    SITE_ID,
    T0,
    FakeControlPlane,
    at,
    make_config,
)

API = "http://control-plane.test"
FRAME_COUNT = 20


def make_scenario(frame_count: int = FRAME_COUNT) -> Scenario:
    return Scenario.from_list(
        [
            {
                "at_seconds": float(second),
                "camera_id": CAMERA_ID,
                "detections": [
                    {
                        "class": "person_without_helmet",
                        "bbox": [0.4, 0.4, 0.6, 0.85],
                        "confidence": 0.9,
                    }
                ],
            }
            for second in range(frame_count)
        ]
    )


@pytest.fixture
def tight_agent(tmp_path: Path) -> Iterator[tuple[EdgeAgent, EdgeStore, FakeControlPlane]]:
    """An agent whose outbox critical threshold fits only a few events."""
    store = EdgeStore(
        tmp_path / "edge.sqlite3",
        warning_bytes=1_500,
        critical_bytes=2_500,
    )
    plane = FakeControlPlane(config_document=make_config().model_dump())
    client = plane.client()
    auth = AgentAuthenticator(client, API, "site:agent:secret")
    scenario = make_scenario()
    agent = EdgeAgent(
        store=store,
        frame_source=SyntheticSource(scenario, start_at=T0),
        detector=SyntheticDetector(scenario),
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
    agent.start(T0)
    agent.config_tick(T0)
    yield agent, store, plane
    store.close()


def test_crossing_critical_halts_opens_gap_and_stops_generation(
    tight_agent, caplog
) -> None:
    agent, store, _ = tight_agent
    frames = list(SyntheticSource(make_scenario(), start_at=T0).frames())
    emitted: list[str] = []
    halted_after: int | None = None
    with caplog.at_level("CRITICAL", logger="guardian_lens_edge.state"):
        for index, frame in enumerate(frames):
            emitted.extend(agent.process_frame(frame))
            if agent.state.state is OperatingState.HALTED:
                halted_after = index
                break
    assert halted_after is not None, "critical threshold never crossed"
    assert emitted, "some events must have been generated before the halt"
    assert agent.state.halt_reason is HaltReason.OUTBOX_FULL
    # The gap is loud and persisted.
    gaps = store.open_gaps()
    assert [gap.reason for gap in gaps] == ["outbox_full"]
    assert gaps[0].camera_id == CAMERA_ID
    assert any(record.levelname == "CRITICAL" for record in caplog.records)

    # Generation has STOPPED: further frames emit nothing, and nothing
    # already buffered was dropped to make room.
    pending_before = store.pending_count()
    for frame in frames[halted_after + 1:halted_after + 4]:
        assert agent.process_frame(frame) == []
    assert store.pending_count() == pending_before


def test_recovery_closes_gap_and_resumes(tight_agent) -> None:
    agent, store, plane = tight_agent
    frames = list(SyntheticSource(make_scenario(), start_at=T0).frames())
    for frame in frames:
        agent.process_frame(frame)
        if agent.state.state is OperatingState.HALTED:
            break
    assert agent.state.state is OperatingState.HALTED
    gap_id = store.open_gaps()[0].gap_id

    # Network restored: the publisher drains the backlog (all 201) and the
    # post-drain level report closes the gap and resumes generation.
    for tick in range(10):
        agent.publisher_tick(at(100 + tick))
        if agent.state.state is OperatingState.HEALTHY:
            break
    assert agent.state.state is OperatingState.HEALTHY
    assert store.open_gaps() == []
    assert agent.state.can_generate() is True

    # The close record reaches the control plane on the next drain.
    agent.publisher_tick(at(200))
    closed = [
        gap for gap in plane.received_gaps
        if gap["id"] == gap_id and gap["ended_at"] is not None
    ]
    assert len(closed) == 1

    # Generation resumes: a fresh frame produces a candidate again.
    resumed_frame = frames[-1]
    assert agent.process_frame(resumed_frame) != []


def test_warning_level_logs_but_does_not_halt(tight_agent, caplog) -> None:
    agent, store, _ = tight_agent
    frames = list(SyntheticSource(make_scenario(), start_at=T0).frames())
    with caplog.at_level("WARNING", logger="guardian_lens_edge.state"):
        for frame in frames:
            agent.process_frame(frame)
            if store.backpressure_level().value != "normal":
                break
    assert any("backlog" in record.message for record in caplog.records)
    assert agent.state.state is OperatingState.HEALTHY
