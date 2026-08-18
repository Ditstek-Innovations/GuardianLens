"""MOD-9 — verified-only reporting with coverage context."""

from __future__ import annotations

import uuid

import pytest

from tests.api.conftest import bearer, create_unverified_event

WINDOW = {"from": "2026-08-01T00:00:00Z", "to": "2026-08-31T23:59:59Z"}


@pytest.fixture(scope="module")
def reported_site(client, api_seed, agent_token, reviewer_token):
    """One accepted, one corrected, one rejected, one left unverified, and
    a 45-minute coverage gap — the whole reporting alphabet."""
    def decide(event_id, body):
        response = client.post(
            f"/api/v1/events/{event_id}/decision",
            json=body,
            headers=bearer(reviewer_token),
        )
        assert response.status_code == 200, response.text

    accepted = create_unverified_event(client, api_seed, agent_token)
    decide(accepted, {"decision": "accept", "version": 1})

    corrected = create_unverified_event(client, api_seed, agent_token)
    decide(
        corrected,
        {
            "decision": "correct",
            "version": 1,
            "corrections": [{"field": "zone_id", "value": str(api_seed["zone_a2"])}],
        },
    )

    rejected = create_unverified_event(client, api_seed, agent_token)
    decide(
        rejected,
        {"decision": "reject", "version": 1, "rejection_reason": "false positive"},
    )

    create_unverified_event(client, api_seed, agent_token)  # stays unverified

    gap = client.post(
        "/api/v1/coverage-gaps",
        json={
            "id": str(uuid.uuid4()),
            "camera_id": str(api_seed["camera_a"]),
            "started_at": "2026-08-12T06:00:00Z",
            "ended_at": "2026-08-12T06:45:00Z",
            "reason": "stream_lost",
        },
        headers=bearer(agent_token),
    )
    assert gap.status_code == 200
    return {"accepted": accepted, "corrected": corrected, "rejected": rejected}


@pytest.mark.active_rule("BR-R-01")
def test_summary_counts_verified_only_and_includes_gaps(
    client, api_seed, manager_token, reported_site
):
    response = client.get(
        "/api/v1/reports/summary",
        params={"site_id": str(api_seed["site_a"]), "group_by": "zone", **WINDOW},
        headers=bearer(manager_token),
    )
    assert response.status_code == 200, response.text
    body = response.json()

    assert body["basis"] == "verified_events_only"
    assert body["coverage_gaps_minutes"] >= 45

    total_verified = sum(g["verified_count"] for g in body["groups"])
    counts = body["decision_counts"]
    # Verified groups hold exactly the accepted + corrected population;
    # the rejected and unverified events are not in any group.
    assert total_verified == counts["accepted"] + counts["corrected"]
    assert counts["rejected"] >= 1  # BR-R-03 — visible, never hidden


@pytest.mark.active_rule("BR-R-01")
def test_summary_by_day_and_rule(client, api_seed, manager_token, reported_site):
    for group_by in ("day", "rule"):
        response = client.get(
            "/api/v1/reports/summary",
            params={
                "site_id": str(api_seed["site_a"]),
                "group_by": group_by,
                **WINDOW,
            },
            headers=bearer(manager_token),
        )
        assert response.status_code == 200
        assert all(g["verified_count"] >= 1 for g in response.json()["groups"])


@pytest.mark.active_rule("BR-R-02")
def test_export_carries_provenance_header(
    client, api_seed, manager_token, reported_site
):
    response = client.get(
        "/api/v1/reports/export",
        params={"site_id": str(api_seed["site_a"]), "group_by": "zone", **WINDOW},
        headers=bearer(manager_token),
    )
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    text = response.text
    assert "# period_from" in text
    assert "# generated_by,Test manager_a" in text
    assert "# basis,verified_events_only" in text
    assert "# coverage_gaps_minutes" in text


def test_summary_out_of_scope_site_is_403(client, api_seed, reviewer_token):
    response = client.get(
        "/api/v1/reports/summary",
        params={"site_id": str(api_seed["site_b"]), **WINDOW},
        headers=bearer(reviewer_token),
    )
    assert response.status_code == 403


def test_summary_rejects_unknown_group_by(client, api_seed, manager_token):
    response = client.get(
        "/api/v1/reports/summary",
        params={
            "site_id": str(api_seed["site_a"]),
            "group_by": "reviewer",  # grouping by a person is not a thing
            **WINDOW,
        },
        headers=bearer(manager_token),
    )
    assert response.status_code == 422
