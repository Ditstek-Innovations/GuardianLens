"""The full loop, end to end: TRD 20.2 steps 1-4 in one test.

    provision tenant -> bootstrap admin + site -> configure camera/zone/rule
    -> activate rule (named user) -> edge agent pulls config, runs a
    scenario, buffers to its outbox -> publishes through the REAL ingest
    route -> reviewer sees the queue -> decides -> report shows the record.

Every hop is the production code path: the tenant is provisioned by
guardian_lens.db.provisioning (FF-11 gate included), configuration flows
through the API with audit entries, the edge agent authenticates with a
real credential exchange and publishes through the real FastAPI app (the
injected httpx client is Starlette's TestClient, which IS an httpx.Client —
no sockets, no mocks on the path).

What this proves that no single suite can: the contracts between the three
independently-built planes actually meet. The edge's payloads validate
against the control plane's schemas; the control plane's config document
round-trips into the edge's evaluator; the reviewer's decision lands on the
event the edge created.
"""

from __future__ import annotations

import json
import os
import uuid
from collections.abc import Iterator
from datetime import datetime, timezone
from pathlib import Path

import psycopg
import pytest
from starlette.testclient import TestClient

from guardian_lens.db.provisioning import deprovision, provision
from guardian_lens.db.urls import psycopg_url, tenant_url

BOOTSTRAP_PASSWORD = "e2e-bootstrap-password-1"  # test-only; env-injected below
ADMIN_EMAIL = f"admin+{uuid.uuid4().hex[:8]}@e2e.test"  # unique per run


@pytest.fixture(scope="module")
def workflow(control_url: str) -> Iterator[dict]:
    """A provisioned tenant with a bootstrapped admin, plus the live app."""
    base = os.environ["GL_TENANT_DB_URL"]
    slug = f"e2e_{uuid.uuid4().hex[:8]}"

    provision(slug, "E2E workflow", base_url=base, control_url=control_url)

    os.environ["GL_BOOTSTRAP_PASSWORD"] = BOOTSTRAP_PASSWORD
    os.environ.setdefault("GL_JWT_SECRET", "e2e-test-secret-not-production")
    from guardian_lens.api.bootstrap import bootstrap

    bootstrap(
        slug,
        ADMIN_EMAIL,
        "E2E Admin",
        site_name="E2E Plant",
        timezone_name="Asia/Kolkata",
        control_url=control_url,
        base_url=base,
    )

    # The agent principal and the model version have no API surface yet
    # (registration endpoints are follow-up work, noted in WORKFLOW.md), so
    # they are seeded the way an operator would: directly, in-tenant.
    from argon2 import PasswordHasher

    agent_id = uuid.uuid4()
    agent_secret = uuid.uuid4().hex
    t_url = tenant_url(base, slug)
    with psycopg.connect(psycopg_url(t_url)) as conn:
        site_id = conn.execute("SELECT id FROM sites").fetchone()[0]
        conn.execute(
            "INSERT INTO agents (id, site_id, name, credential_hash) "
            "VALUES (%s, %s, 'e2e-edge', %s)",
            (agent_id, site_id, PasswordHasher().hash(agent_secret)),
        )
        conn.execute(
            "INSERT INTO model_versions (version, artefact_hash, classes) "
            "VALUES ('synthetic-0.0.0', 'sha256:synthetic', '[\"person_without_helmet\"]')"
        )
        conn.commit()

    from guardian_lens.api.app import create_app

    with TestClient(create_app()) as client:
        yield {
            "slug": slug,
            "client": client,
            "site_id": str(site_id),
            "agent_id": str(agent_id),
            "agent_credential": f"{slug}:{agent_id}:{agent_secret}",
        }

    deprovision(slug, base_url=base, control_url=control_url)


def _login(client: TestClient) -> dict:
    response = client.post(
        "/api/v1/auth/login",
        json={"email": ADMIN_EMAIL, "password": BOOTSTRAP_PASSWORD},
    )
    assert response.status_code == 200, response.text
    return response.json()


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def test_full_workflow(workflow, tmp_path: Path):
    client: TestClient = workflow["client"]
    site_id = workflow["site_id"]

    # ---- 1. Admin configures the site through the API -------------------
    token = _login(client)["access_token"]

    camera = client.post(
        "/api/v1/cameras",
        headers=_auth(token),
        json={
            "site_id": site_id,
            "name": "Bay 3 entrance",
            "stream_url": "rtsp://user:pass@10.0.0.5/stream2",
        },
    )
    assert camera.status_code == 201, camera.text
    camera_id = camera.json()["id"]
    # The credential never comes back (BR-S-03).
    assert "stream_url" not in camera.text

    zone = client.post(
        "/api/v1/zones",
        headers=_auth(token),
        json={
            "camera_id": camera_id,
            "name": "Bay 3",
            "polygon": [[0.0, 0.0], [1.0, 0.0], [1.0, 1.0], [0.0, 1.0]],
        },
    )
    assert zone.status_code == 201, zone.text
    zone_id = zone.json()["id"]

    rule = client.post(
        "/api/v1/rules",
        headers=_auth(token),
        json={
            "zone_id": zone_id,
            "rule_type": "ppe_helmet",
            "confidence_threshold": 0.5,
            "debounce_seconds": 30,
            "human_readable": "Helmet required in Bay 3",
        },
    )
    assert rule.status_code == 201, rule.text
    rule_id = rule.json()["id"]
    assert rule.json()["is_active"] is False  # BR-001: nothing by default

    activated = client.post(
        f"/api/v1/rules/{rule_id}/activate", headers=_auth(token)
    )
    assert activated.status_code == 200, activated.text
    assert activated.json()["activated_by"] is not None  # BR-C-02

    # ---- 2. The edge agent runs a scenario against the live app ---------
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

    scenario_path = tmp_path / "scenario.json"
    scenario_path.write_text(json.dumps([
        {
            "at_seconds": 0.0,
            "camera_id": camera_id,
            "detections": [{
                "class": "person_without_helmet",
                "bbox": [0.4, 0.4, 0.6, 0.85],
                "confidence": 0.83,
            }],
        },
        {"at_seconds": 1.0, "camera_id": camera_id, "detections": []},
    ]))
    scenario = Scenario.load(scenario_path)
    now = datetime(2026, 8, 12, 9, 0, 0, tzinfo=timezone.utc)

    store = EdgeStore(
        tmp_path / "outbox.db",
        warning_bytes=50 * 1024 * 1024,
        critical_bytes=100 * 1024 * 1024,
    )
    authenticator = AgentAuthenticator(
        client, "http://testserver", workflow["agent_credential"]
    )
    state = AgentStateMachine(
        store,
        failure_window=50,
        degraded_failure_rate=0.2,
        halt_failure_rate=0.5,
    )
    agent = EdgeAgent(
        store=store,
        frame_source=SyntheticSource(scenario, start_at=now),
        detector=SyntheticDetector(scenario),
        evaluator=RuleEvaluator(store),
        builder=EventBuilder(store, tmp_path / "spool", workflow["agent_id"]),
        publisher=Publisher(store, client, "http://testserver", authenticator),
        config_sync=ConfigSync(
            store, client, "http://testserver", workflow["agent_id"],
            authenticator,
        ),
        state=state,
        agent_id=workflow["agent_id"],
        site_id=site_id,
    )

    event_ids = agent.run_scenario(now=now)
    assert len(event_ids) == 1, (
        "the scenario contains exactly one admissible detection"
    )
    agent.publisher_tick(now)
    assert store.pending_count() == 0, "the outbox must fully drain"

    # ---- 3. The reviewer sees exactly what the edge observed ------------
    queue = client.get(
        "/api/v1/events", headers=_auth(token), params={"status": "unverified"}
    )
    assert queue.status_code == 200, queue.text
    items = queue.json()["items"]
    assert len(items) == 1
    event = items[0]
    assert event["status"] == "unverified"

    # The queue row deliberately omits rule_snapshot (DATABASE.md 7.3 —
    # the queue never needs the JSONB); the detail carries it.
    detail = client.get(f"/api/v1/events/{event['id']}", headers=_auth(token))
    assert detail.status_code == 200, detail.text
    snapshot = detail.json()["rule_snapshot"]
    assert snapshot["human_readable"] == "Helmet required in Bay 3"
    event = detail.json()

    evidence = client.get(
        f"/api/v1/events/{event['id']}/evidence", headers=_auth(token)
    )
    assert evidence.status_code == 200
    assert evidence.content.startswith(b"\xff\xd8")  # a real JPEG

    # ---- 4. The human gate ---------------------------------------------
    decision = client.post(
        f"/api/v1/events/{event['id']}/decision",
        headers=_auth(token),
        json={"decision": "accept", "version": event["version"]},
    )
    assert decision.status_code == 200, decision.text
    decided = decision.json()
    assert decided["status"] == "accepted"
    # BR-005: the record names its reviewer — as a person, not a bare id.
    assert decided["reviewer"]["full_name"] == "E2E Admin"
    assert decided["decided_at"] is not None

    # A second decision on the same event is refused with the first one.
    again = client.post(
        f"/api/v1/events/{event['id']}/decision",
        headers=_auth(token),
        json={"decision": "reject", "version": event["version"],
              "rejection_reason": "should not land"},
    )
    assert again.status_code == 409  # BR-V-01

    # ---- 5. The record reaches the report -------------------------------
    summary = client.get(
        "/api/v1/reports/summary",
        headers=_auth(token),
        params={
            "site_id": site_id,
            "from": "2026-08-12T00:00:00Z",
            "to": "2026-08-13T00:00:00Z",
            "group_by": "rule",
        },
    )
    assert summary.status_code == 200, summary.text
    report = summary.json()
    assert report["basis"] == "verified_events_only"  # BR-R-01
    assert report["decision_counts"]["accepted"] == 1
    assert sum(g["verified_count"] for g in report["groups"]) == 1

    # ---- 6. Every step left its audit trail ------------------------------
    audit = client.get("/api/v1/audit", headers=_auth(token))
    assert audit.status_code == 200
    actions = [entry["action"] for entry in audit.json()["items"]]
    assert "event.decided" in actions
    assert any(a.startswith("rule.activated") for a in actions)  # BR-010


def test_agent_token_cannot_decide_and_human_cannot_ingest(workflow):
    """The two principal types stay on their own sides of the gate."""
    client: TestClient = workflow["client"]

    agent_token = client.post(
        "/api/v1/auth/agent",
        json={"credential": workflow["agent_credential"]},
    ).json()["access_token"]

    # An agent cannot even list the queue, let alone decide (BR-S-02).
    assert client.get(
        "/api/v1/events", headers=_auth(agent_token)
    ).status_code == 403

    human_token = _login(client)["access_token"]
    assert client.post(
        "/api/v1/events",
        headers=_auth(human_token),
        json={},
    ).status_code == 403
