"""MOD-7 — the D2 decision ladder, transactionality, and scope.

Covers every API row of the bypass suite that touches the decision path
(TRD 19.4), plus the BR-AU-03 rollback that only an integration test can
prove.
"""

from __future__ import annotations

import uuid

import pytest

from guardian_lens.services.audit import AuditService
from tests.api.conftest import bearer, create_unverified_event


def _decide(client, token, event_id, body):
    return client.post(
        f"/api/v1/events/{event_id}/decision", json=body, headers=bearer(token)
    )


def _audit_rows(conn, event_id):
    return conn.execute(
        "SELECT action, actor_user_id FROM audit_log"
        " WHERE entity_type = 'event' AND entity_id = %s",
        (event_id,),
    ).fetchall()


@pytest.mark.active_rule("BR-004")
def test_accept_happy_path_writes_event_and_audit_atomically(
    client, api_seed, agent_token, reviewer_token, tenant_conn
):
    event_id = create_unverified_event(client, api_seed, agent_token)
    response = _decide(
        client, reviewer_token, event_id, {"decision": "accept", "version": 1}
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "accepted"
    assert body["version"] == 2
    assert body["reviewer"]["id"] == str(api_seed["reviewer_a"])

    row = tenant_conn.execute(
        "SELECT status, reviewer_id, decided_at FROM events WHERE id = %s",
        (event_id,),
    ).fetchone()
    assert row[0] == "accepted"
    assert str(row[1]) == str(api_seed["reviewer_a"])
    assert row[2] is not None

    audit = _audit_rows(tenant_conn, event_id)
    assert [a[0] for a in audit] == ["event.decided"]
    assert str(audit[0][1]) == str(api_seed["reviewer_a"])


@pytest.mark.proposed_rule("BR-S-02")
def test_agent_token_cannot_decide(client, api_seed, agent_token):
    """Bypass row: authenticate as an agent and attempt a decision → 403."""
    event_id = create_unverified_event(client, api_seed, agent_token)
    response = _decide(
        client, agent_token, event_id, {"decision": "accept", "version": 1}
    )
    assert response.status_code == 403


def test_auditor_cannot_decide(client, api_seed, agent_token, auditor_token):
    """TRD 12.3 — auditor is read-only; D2 step 2."""
    event_id = create_unverified_event(client, api_seed, agent_token)
    response = _decide(
        client, auditor_token, event_id, {"decision": "accept", "version": 1}
    )
    assert response.status_code == 403


@pytest.mark.active_rule("BR-S-01")
def test_reviewer_id_in_body_is_400(
    client, api_seed, agent_token, reviewer_token, tenant_conn
):
    """Bypass row: supply reviewer_id in the decision body → 400, identity
    from token only."""
    event_id = create_unverified_event(client, api_seed, agent_token)
    response = _decide(
        client,
        reviewer_token,
        event_id,
        {
            "decision": "accept",
            "version": 1,
            "reviewer_id": str(api_seed["admin"]),
        },
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "GL-4002"
    status = tenant_conn.execute(
        "SELECT status FROM events WHERE id = %s", (event_id,)
    ).fetchone()[0]
    assert status == "unverified"


def test_bulk_decision_routes_do_not_exist(client, reviewer_token):
    """Bypass row: the bulk decision endpoint answers 404 because it does
    not exist (TRD 10.9, FR-047, DP-3)."""
    for path in ("/api/v1/events/decisions", "/api/v1/events/decision",
                 "/api/v1/decisions/bulk"):
        response = client.post(
            path,
            json={"decision": "accept", "event_ids": [str(uuid.uuid4())]},
            headers=bearer(reviewer_token),
        )
        # 404 outright, or 405 where the path collides with the GET
        # detail route's pattern — either way, no bulk operation exists.
        assert response.status_code in (404, 405), path


@pytest.mark.proposed_rule("BR-V-01")
def test_second_decision_is_409_with_existing_decision(
    client, api_seed, agent_token, reviewer_token, manager_token
):
    event_id = create_unverified_event(client, api_seed, agent_token)
    first = _decide(
        client, reviewer_token, event_id, {"decision": "accept", "version": 1}
    )
    assert first.status_code == 200
    second = _decide(
        client, manager_token, event_id, {"decision": "accept", "version": 2}
    )
    assert second.status_code == 409
    error = second.json()["error"]
    assert error["code"] == "GL-4090"
    existing = error["existing_decision"]
    assert existing["status"] == "accepted"
    assert existing["reviewer_id"] == str(api_seed["reviewer_a"])


def test_stale_version_is_409(client, api_seed, agent_token, reviewer_token):
    event_id = create_unverified_event(client, api_seed, agent_token)
    response = _decide(
        client, reviewer_token, event_id, {"decision": "accept", "version": 99}
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "GL-4091"


def test_reject_requires_reason(client, api_seed, agent_token, reviewer_token):
    event_id = create_unverified_event(client, api_seed, agent_token)
    response = _decide(
        client, reviewer_token, event_id, {"decision": "reject", "version": 1}
    )
    assert response.status_code == 422
    assert response.json()["error"]["field"] == "rejection_reason"


@pytest.mark.active_rule("BR-007")
def test_reject_with_reason_is_recorded(
    client, api_seed, agent_token, reviewer_token, tenant_conn
):
    event_id = create_unverified_event(client, api_seed, agent_token)
    response = _decide(
        client,
        reviewer_token,
        event_id,
        {
            "decision": "reject",
            "version": 1,
            "rejection_reason": "Helmet was carried, not required in transit",
        },
    )
    assert response.status_code == 200
    assert response.json()["status"] == "rejected"
    row = tenant_conn.execute(
        "SELECT status, rejection_reason FROM events WHERE id = %s", (event_id,)
    ).fetchone()
    assert row[0] == "rejected" and row[1] is not None


def test_correction_retains_original_value(
    client, api_seed, agent_token, reviewer_token, tenant_conn
):
    """A correct decision amends the field AND retains the model's original
    output — the only ground truth the product collects."""
    event_id = create_unverified_event(client, api_seed, agent_token)
    response = _decide(
        client,
        reviewer_token,
        event_id,
        {
            "decision": "correct",
            "version": 1,
            "corrections": [
                {"field": "zone_id", "value": str(api_seed["zone_a2"])}
            ],
        },
    )
    assert response.status_code == 200, response.text
    assert response.json()["status"] == "corrected"
    correction = tenant_conn.execute(
        "SELECT field_name, original_value, corrected_value"
        " FROM event_corrections WHERE event_id = %s",
        (event_id,),
    ).fetchone()
    assert correction[0] == "zone_id"
    assert correction[1] == str(api_seed["zone_a"])
    assert correction[2] == str(api_seed["zone_a2"])
    zone_now = tenant_conn.execute(
        "SELECT zone_id FROM events WHERE id = %s", (event_id,)
    ).fetchone()[0]
    assert str(zone_now) == str(api_seed["zone_a2"])


def test_correct_requires_corrections(client, api_seed, agent_token, reviewer_token):
    event_id = create_unverified_event(client, api_seed, agent_token)
    response = _decide(
        client, reviewer_token, event_id, {"decision": "correct", "version": 1}
    )
    assert response.status_code == 422


def test_uncorrectable_field_is_422(client, api_seed, agent_token, reviewer_token):
    event_id = create_unverified_event(client, api_seed, agent_token)
    response = _decide(
        client,
        reviewer_token,
        event_id,
        {
            "decision": "correct",
            "version": 1,
            "corrections": [{"field": "confidence", "value": "0.99"}],
        },
    )
    assert response.status_code == 422


@pytest.mark.proposed_rule("BR-AU-03")
def test_audit_failure_rolls_back_the_decision(
    client, api_seed, agent_token, reviewer_token, tenant_conn, monkeypatch
):
    """Bypass-adjacent integration row (TRD 19.3): if the audit insert
    fails, the decision must not exist — no orphan record."""
    event_id = create_unverified_event(client, api_seed, agent_token)

    def refuse(self, **kwargs):  # noqa: ANN001, ANN003
        raise RuntimeError("audit store unavailable (injected)")

    monkeypatch.setattr(AuditService, "write", refuse)
    response = _decide(
        client, reviewer_token, event_id, {"decision": "accept", "version": 1}
    )
    assert response.status_code == 500
    monkeypatch.undo()

    row = tenant_conn.execute(
        "SELECT status, reviewer_id, version FROM events WHERE id = %s",
        (event_id,),
    ).fetchone()
    assert row[0] == "unverified"
    assert row[1] is None
    assert row[2] == 1  # the version bump rolled back with everything else
    assert _audit_rows(tenant_conn, event_id) == []


@pytest.mark.tenancy
def test_reviewer_scoped_to_site_a_cannot_read_site_b_event(
    client, api_seed, agent_b_token, reviewer_token
):
    """Repository-level scope: site B's event does not exist for a site A
    reviewer — 404, not 403, so existence does not leak."""
    event_id = create_unverified_event(
        client,
        api_seed,
        agent_b_token,
        camera_id=str(api_seed["camera_b"]),
        zone_id=str(api_seed["zone_b"]),
        rule_id=str(api_seed["rule_b"]),
    )
    response = client.get(
        f"/api/v1/events/{event_id}", headers=bearer(reviewer_token)
    )
    assert response.status_code == 404
    evidence = client.get(
        f"/api/v1/events/{event_id}/evidence", headers=bearer(reviewer_token)
    )
    assert evidence.status_code == 404


@pytest.mark.tenancy
def test_reviewer_scoped_to_site_a_cannot_decide_site_b_event(
    client, api_seed, agent_b_token, reviewer_token, tenant_conn
):
    """D2 step 3: out of scope → 403 on the decision path."""
    event_id = create_unverified_event(
        client,
        api_seed,
        agent_b_token,
        camera_id=str(api_seed["camera_b"]),
        zone_id=str(api_seed["zone_b"]),
        rule_id=str(api_seed["rule_b"]),
    )
    response = _decide(
        client, reviewer_token, event_id, {"decision": "accept", "version": 1}
    )
    assert response.status_code == 403
    status = tenant_conn.execute(
        "SELECT status FROM events WHERE id = %s", (event_id,)
    ).fetchone()[0]
    assert status == "unverified"


def test_queue_is_scoped_and_cursor_paginated(
    client, api_seed, agent_token, agent_b_token, reviewer_token
):
    """The queue never shows another site's events, pages stably on
    (received_at, id), and reports queue_depth on every response."""
    for _ in range(3):
        create_unverified_event(client, api_seed, agent_token)
    site_b_event = create_unverified_event(
        client,
        api_seed,
        agent_b_token,
        camera_id=str(api_seed["camera_b"]),
        zone_id=str(api_seed["zone_b"]),
        rule_id=str(api_seed["rule_b"]),
    )

    seen: list[str] = []
    cursor = None
    while True:
        params = {"limit": 2}
        if cursor:
            params["cursor"] = cursor
        page = client.get(
            "/api/v1/events", params=params, headers=bearer(reviewer_token)
        )
        assert page.status_code == 200
        body = page.json()
        assert body["queue_depth"] >= 3
        seen.extend(item["id"] for item in body["items"])
        cursor = body["next_cursor"]
        if cursor is None:
            break

    assert len(seen) == len(set(seen)), "cursor paging returned a duplicate"
    assert site_b_event not in seen
