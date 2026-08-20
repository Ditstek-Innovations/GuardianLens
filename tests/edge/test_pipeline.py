"""E2E-ish: scenario file → frames → detector → D1 → builder → outbox →
publisher → (mock) control plane. No network, no ML, no Postgres."""

from __future__ import annotations

import base64
import json
import uuid
from pathlib import Path

from guardian_lens_edge.agent import EdgeAgent
from guardian_lens_edge.auth import AgentAuthenticator
from guardian_lens_edge.config_sync import ConfigSync
from guardian_lens_edge.detector import SyntheticDetector
from guardian_lens_edge.events import EventBuilder
from guardian_lens_edge.frames import SyntheticSource
from guardian_lens_edge.publisher import Publisher
from guardian_lens_edge.rules import RuleEvaluator
from guardian_lens_edge.scenario import Scenario
from guardian_lens_edge.state import AgentStateMachine
from guardian_lens_edge.store import EdgeStore

from tests.edge.conftest import (
    AGENT_ID,
    CAMERA_ID,
    RULE_ID,
    SITE_ID,
    T0,
    ZONE_ID,
    FakeControlPlane,
    at,
    make_config,
)

API = "http://control-plane.test"

SCENARIO = [
    # t=0: admitted -> candidate.
    {
        "at_seconds": 0.0,
        "camera_id": CAMERA_ID,
        "detections": [
            {"class": "person_without_helmet",
             "bbox": [0.4, 0.4, 0.6, 0.85], "confidence": 0.83}
        ],
    },
    # t=1: below threshold -> discarded + counted.
    {
        "at_seconds": 1.0,
        "camera_id": CAMERA_ID,
        "detections": [
            {"class": "person_without_helmet",
             "bbox": [0.4, 0.4, 0.6, 0.85], "confidence": 0.2}
        ],
    },
    # t=2: anchor outside the zone -> discarded + counted.
    {
        "at_seconds": 2.0,
        "camera_id": CAMERA_ID,
        "detections": [
            {"class": "person_without_helmet",
             "bbox": [0.4, 0.5, 0.6, 0.95], "confidence": 0.9}
        ],
    },
    # t=3: admitted again but within the 30s debounce -> suppressed + counted.
    {
        "at_seconds": 3.0,
        "camera_id": CAMERA_ID,
        "detections": [
            {"class": "person_without_helmet",
             "bbox": [0.4, 0.4, 0.6, 0.85], "confidence": 0.9}
        ],
    },
]


def build_agent(
    tmp_path: Path, plane: FakeControlPlane, scenario: Scenario
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
    return agent, store


def scenario_from_file(tmp_path: Path) -> Scenario:
    scenario_path = tmp_path / "scenario.json"
    scenario_path.write_text(json.dumps(SCENARIO), encoding="utf-8")
    return Scenario.load(scenario_path)


def test_scenario_to_outbox_payload_shape(tmp_path: Path) -> None:
    """The candidate lands in the outbox with the exact TRD 10.3 shape."""
    scenario = scenario_from_file(tmp_path)
    plane = FakeControlPlane()  # never contacted in this test
    agent, store = build_agent(tmp_path, plane, scenario)
    config = make_config(debounce_seconds=30)
    # Configuration was applied on an earlier run; restored as
    # last-known-good with the control plane never contacted (ADR-008).
    store.save_config(1, config.model_dump(),
                      applied_at="2026-08-12T08:00:00+00:00")
    agent.start(T0)
    emitted: list[str] = []
    for frame in SyntheticSource(scenario, start_at=T0).frames():
        emitted.extend(agent.process_frame(frame))

    assert len(emitted) == 1
    rows = store.claim_batch(10, now="x")
    assert [row.kind for row in rows] == ["event"]
    payload = rows[0].payload

    # Exact ingest contract keys — nothing extra, nothing missing.
    assert set(payload) == {
        "event_id", "camera_id", "zone_id", "rule_id", "rule_snapshot",
        "source", "model_version", "confidence", "occurred_at", "evidence",
    }
    # The edge NEVER sets status (TRD 5.4 layer 1).
    assert "status" not in payload
    event_id = uuid.UUID(payload["event_id"])
    assert event_id.version == 7
    assert payload["camera_id"] == CAMERA_ID
    assert payload["zone_id"] == ZONE_ID
    assert payload["rule_id"] == RULE_ID
    assert payload["source"] == "guardian_lens"
    assert payload["model_version"] == "synthetic-0.0.0"
    assert payload["confidence"] == 0.83
    assert payload["occurred_at"] == "2026-08-12T09:00:00Z"
    # rule_snapshot is the FULL rule as configured at detection time.
    assert payload["rule_snapshot"] == config.rules[0].model_dump()
    # The spooled evidence is a structurally valid JPEG.
    evidence_bytes = Path(rows[0].evidence_path).read_bytes()
    assert evidence_bytes.startswith(b"\xff\xd8")
    assert evidence_bytes.endswith(b"\xff\xd9")

    # Every discard path was counted, never silently dropped (BR-D-02).
    counters = store.counters()[0]
    assert counters["below_threshold"] == 1
    assert counters["outside_zone"] == 1
    assert counters["debounce_suppressed"] == 1
    assert counters["dwell_unmet"] == 0


def test_run_scenario_delivers_event_and_health(tmp_path: Path) -> None:
    scenario = scenario_from_file(tmp_path)
    plane = FakeControlPlane(
        config_document=make_config(debounce_seconds=30).model_dump()
    )
    agent, store = build_agent(tmp_path, plane, scenario)
    emitted = agent.run_scenario(now=T0)
    assert len(emitted) == 1

    # The event reached the mock control plane with evidence embedded.
    assert len(plane.received_events) == 1
    delivered = plane.received_events[0]
    assert delivered["event_id"] == emitted[0]
    assert "status" not in delivered
    frame_bytes = base64.b64decode(delivered["evidence"]["data_b64"])
    assert frame_bytes.startswith(b"\xff\xd8")

    # The health beat is enqueued (delivered on the next drain) and carries
    # the applied config version and sent_at for skew measurement (ADR-007).
    agent.publisher_tick(at(100))
    assert len(plane.received_health) == 1
    health = plane.received_health[0]
    # Exactly the control plane's AgentHealthRequest (extra="forbid"):
    # identity comes from the agent token, richer state stays local.
    assert set(health) == {
        "sent_at",
        "applied_config_version",
        "agent_version",
        "review_block",
    }
    assert isinstance(health["review_block"], list)
    assert health["applied_config_version"] == 1
    assert health["sent_at"] == "2026-08-12T09:00:03Z"

    # Everything delivered: the outbox is empty and spool reclaimed.
    assert store.pending_count() == 0
    assert store.parked_rows() == []
    store.close()


def test_inactive_rule_scenario_records_nothing(tmp_path: Path) -> None:
    """BR-001 end to end: an inactive rule produces no event, no counter."""
    scenario = scenario_from_file(tmp_path)
    plane = FakeControlPlane(
        config_document=make_config(is_active=False).model_dump()
    )
    agent, store = build_agent(tmp_path, plane, scenario)
    emitted = agent.run_scenario(now=T0)
    assert emitted == []
    assert plane.received_events == []
    assert store.counters() == []
    store.close()
