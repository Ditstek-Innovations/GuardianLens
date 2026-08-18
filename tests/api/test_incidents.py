"""GET /events/incidents — display-level grouping of the review queue.

Grouping collapses the VIEW only. BR-V-02 stays load-bearing: there is no
incident-level decision route, and these tests assert the group carries its
members' ids for one-by-one decisions rather than any bulk affordance.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

from guardian_lens.repositories.events import sessionize
from tests.api.conftest import bearer, create_unverified_event


# -- sessionize: pure unit ----------------------------------------------------


def _row(rule_id, at, event_id=None):
    return SimpleNamespace(
        rule_id=rule_id,
        occurred_at=at,
        id=event_id or uuid.uuid4(),
        received_at=at,
    )


def test_sessionize_groups_consecutive_same_rule_within_gap():
    rule = uuid.uuid4()
    base = datetime(2026, 8, 14, 9, 0, tzinfo=timezone.utc)
    rows = [
        _row(rule, base),
        _row(rule, base + timedelta(seconds=30)),
        _row(rule, base + timedelta(seconds=60)),
        # 20 minutes of quiet: a new incident, same rule.
        _row(rule, base + timedelta(minutes=21)),
    ]
    groups = sessionize(rows, gap_seconds=300)
    assert [len(g) for g in groups] == [3, 1]


def test_sessionize_never_merges_across_rules():
    rule_a, rule_b = uuid.uuid4(), uuid.uuid4()
    base = datetime(2026, 8, 14, 9, 0, tzinfo=timezone.utc)
    rows = [
        _row(rule_a, base),
        _row(rule_a, base + timedelta(seconds=30)),
        _row(rule_b, base + timedelta(seconds=31)),
    ]
    groups = sessionize(rows, gap_seconds=300)
    assert [len(g) for g in groups] == [2, 1]


def test_sessionize_isolates_ruleless_rows():
    """An NVR event with no rule can never claim 'same condition'."""
    base = datetime(2026, 8, 14, 9, 0, tzinfo=timezone.utc)
    rows = [_row(None, base), _row(None, base + timedelta(seconds=1))]
    groups = sessionize(rows, gap_seconds=300)
    assert [len(g) for g in groups] == [1, 1]


# -- the route, against the real database ------------------------------------


@pytest.mark.tenancy
def test_incident_grouping_folds_bursts_and_scopes_by_site(
    client, api_seed, agent_token, agent_b_token, reviewer_token
):
    # A burst well away from other tests' default timestamps.
    burst = [
        create_unverified_event(
            client, api_seed, agent_token,
            occurred_at=f"2026-08-10T05:00:{s:02d}Z",
        )
        for s in (0, 30)
    ]
    later = create_unverified_event(
        client, api_seed, agent_token, occurred_at="2026-08-10T06:00:00Z"
    )
    other_site = create_unverified_event(
        client,
        api_seed,
        agent_b_token,
        camera_id=str(api_seed["camera_b"]),
        zone_id=str(api_seed["zone_b"]),
        rule_id=str(api_seed["rule_b"]),
        occurred_at="2026-08-10T05:00:10Z",
    )

    response = client.get(
        "/api/v1/events/incidents", headers=bearer(reviewer_token)
    )
    assert response.status_code == 200
    body = response.json()
    assert body["capped"] is False

    by_membership = {}
    for incident in body["incidents"]:
        for event_id in incident["event_ids"]:
            by_membership[event_id] = incident

    # The 30s-apart pair folds into one incident; the one-hour-later
    # candidate starts a new one.
    assert by_membership[burst[0]] is by_membership[burst[1]]
    assert by_membership[burst[0]]["count"] >= 2
    assert by_membership[later] is not by_membership[burst[0]]
    # Members are ordered oldest-first for one-by-one review.
    ids = by_membership[burst[0]]["event_ids"]
    assert ids.index(burst[0]) < ids.index(burst[1])
    # Reviewer scoped to site A never sees site B's event anywhere.
    assert other_site not in by_membership
