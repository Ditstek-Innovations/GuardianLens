"""MOD-6 — ingest: idempotency, forbidden fields, principal typing."""

from __future__ import annotations

import base64
import uuid
from datetime import datetime, timedelta, timezone

import pytest

from tests.api.conftest import (
    FRAME_BYTES,
    bearer,
    create_unverified_event,
    ingest_payload,
)


def test_ingest_happy_path_creates_unverified_event(
    client, api_seed, agent_token, tenant_conn
):
    response = client.post(
        "/api/v1/events",
        json=ingest_payload(api_seed),
        headers=bearer(agent_token),
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["status"] == "unverified"
    row = tenant_conn.execute(
        "SELECT status, site_id, evidence_state, evidence_ref FROM events"
        " WHERE id = %s",
        (body["id"],),
    ).fetchone()
    assert row[0] == "unverified"
    assert str(row[1]) == str(api_seed["site_a"])  # derived from the camera
    assert row[2] == "present" and row[3] is not None


@pytest.mark.active_rule("BR-004")
def test_duplicate_event_id_returns_existing_resource(
    client, api_seed, agent_token, tenant_conn
):
    """TRD 10.3 — idempotent: 200 with the existing record, no duplicate."""
    payload = ingest_payload(api_seed)
    first = client.post(
        "/api/v1/events", json=payload, headers=bearer(agent_token)
    )
    assert first.status_code == 201
    second = client.post(
        "/api/v1/events", json=payload, headers=bearer(agent_token)
    )
    assert second.status_code == 200
    assert second.json()["id"] == first.json()["id"]
    count = tenant_conn.execute(
        "SELECT count(*) FROM events WHERE event_id = %s",
        (payload["event_id"],),
    ).fetchone()[0]
    assert count == 1


@pytest.mark.active_rule("BR-004")
@pytest.mark.parametrize("field", ["status", "reviewer_id", "decided_at"])
def test_server_owned_field_in_ingest_is_400(client, api_seed, agent_token, field):
    """The bypass suite's API row: setting status via ingest is 400 — a
    rule violation, not a validation slip."""
    payload = ingest_payload(api_seed)
    payload[field] = "accepted" if field == "status" else str(uuid.uuid4())
    response = client.post(
        "/api/v1/events", json=payload, headers=bearer(agent_token)
    )
    assert response.status_code == 400
    error = response.json()["error"]
    assert error["code"] == "GL-4002"
    assert "BR-004" in error["message"]


@pytest.mark.proposed_rule("BR-S-02")
def test_human_token_cannot_ingest(client, api_seed, admin_token):
    """The mirror of agent isolation: a human token can never hit ingest."""
    response = client.post(
        "/api/v1/events",
        json=ingest_payload(api_seed),
        headers=bearer(admin_token),
    )
    assert response.status_code == 403


def test_unauthenticated_ingest_is_401(client, api_seed):
    assert client.post("/api/v1/events", json=ingest_payload(api_seed)).status_code == 401


def test_unknown_camera_is_422(client, api_seed, agent_token):
    response = client.post(
        "/api/v1/events",
        json=ingest_payload(api_seed, camera_id=str(uuid.uuid4())),
        headers=bearer(agent_token),
    )
    assert response.status_code == 422
    assert response.json()["error"]["field"] == "camera_id"


def test_camera_of_another_site_is_422(client, api_seed, agent_token):
    """agent_a is bound to site A; site B's camera does not exist for it."""
    response = client.post(
        "/api/v1/events",
        json=ingest_payload(api_seed, camera_id=str(api_seed["camera_b"])),
        headers=bearer(agent_token),
    )
    assert response.status_code == 422


def test_future_occurred_at_is_422(client, api_seed, agent_token):
    future = (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat()
    response = client.post(
        "/api/v1/events",
        json=ingest_payload(api_seed, occurred_at=future),
        headers=bearer(agent_token),
    )
    assert response.status_code == 422
    assert response.json()["error"]["field"] == "occurred_at"


def test_unregistered_model_version_is_422(client, api_seed, agent_token):
    response = client.post(
        "/api/v1/events",
        json=ingest_payload(api_seed, model_version="9.9.9-unknown"),
        headers=bearer(agent_token),
    )
    assert response.status_code == 422


def test_oversized_evidence_is_413(client, api_seed, agent_token):
    huge = base64.b64encode(b"\xff" * (70 * 1024)).decode()  # limit is 64 KiB
    payload = ingest_payload(api_seed)
    payload["evidence"]["data_b64"] = huge
    response = client.post(
        "/api/v1/events", json=payload, headers=bearer(agent_token)
    )
    assert response.status_code == 413


def test_unknown_extra_field_is_422_not_400(client, api_seed, agent_token):
    """extra="forbid" catches unknown fields as validation errors; only the
    three server-owned fields get the rule's 400."""
    response = client.post(
        "/api/v1/events",
        json=ingest_payload(api_seed, some_new_field="x"),
        headers=bearer(agent_token),
    )
    assert response.status_code == 422


def test_agent_health_updates_agent_row(client, api_seed, agent_token, tenant_conn):
    sent = datetime.now(timezone.utc).isoformat()
    response = client.post(
        "/api/v1/agents/health",
        json={"sent_at": sent, "applied_config_version": 3,
              "agent_version": "0.9.1"},
        headers=bearer(agent_token),
    )
    assert response.status_code == 200
    assert isinstance(response.json()["clock_skew_ms"], int)
    row = tenant_conn.execute(
        "SELECT last_health_at, applied_config_version, clock_skew_ms, status"
        " FROM agents WHERE id = %s",
        (api_seed["agent_a"],),
    ).fetchone()
    assert row[0] is not None
    assert row[1] == 3
    assert row[2] is not None
    assert row[3] == "active"


def test_agent_health_rejects_human_token(client, admin_token):
    response = client.post(
        "/api/v1/agents/health",
        json={"sent_at": datetime.now(timezone.utc).isoformat()},
        headers=bearer(admin_token),
    )
    assert response.status_code == 403


def test_coverage_gap_upsert_is_idempotent(
    client, api_seed, agent_token, tenant_conn
):
    gap_id = str(uuid.uuid4())
    first = client.post(
        "/api/v1/coverage-gaps",
        json={
            "id": gap_id,
            "camera_id": str(api_seed["camera_a"]),
            "started_at": "2026-08-12T08:00:00Z",
            "reason": "stream_lost",
        },
        headers=bearer(agent_token),
    )
    assert first.status_code == 200
    # Redelivery with the close of the same gap: same row, now ended.
    second = client.post(
        "/api/v1/coverage-gaps",
        json={
            "id": gap_id,
            "camera_id": str(api_seed["camera_a"]),
            "started_at": "2026-08-12T08:00:00Z",
            "ended_at": "2026-08-12T08:30:00Z",
            "reason": "stream_lost",
        },
        headers=bearer(agent_token),
    )
    assert second.status_code == 200
    rows = tenant_conn.execute(
        "SELECT ended_at FROM coverage_gaps WHERE id = %s", (gap_id,)
    ).fetchall()
    assert len(rows) == 1
    assert rows[0][0] is not None


def test_evidence_roundtrip(client, api_seed, agent_token, reviewer_token):
    """The stored frame comes back byte-identical, with the private cache
    header, through the object-authorised route."""
    event_id = create_unverified_event(client, api_seed, agent_token)
    response = client.get(
        f"/api/v1/events/{event_id}/evidence", headers=bearer(reviewer_token)
    )
    assert response.status_code == 200
    assert response.headers["content-type"] == "image/jpeg"
    assert response.headers["cache-control"] == "private, max-age=300"
    assert response.content == FRAME_BYTES


def test_agent_token_cannot_read_evidence(client, api_seed, agent_token):
    event_id = create_unverified_event(client, api_seed, agent_token)
    response = client.get(
        f"/api/v1/events/{event_id}/evidence", headers=bearer(agent_token)
    )
    assert response.status_code == 403
