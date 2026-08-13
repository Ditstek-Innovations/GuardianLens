"""DB-1, DB-2, DB-5, DB-20 — the human verification gate, at the data layer.

TRD 19.4: a suite that ACTIVELY ATTEMPTS to violate every ABSOLUTE rule.
"If it passes, the product's core commitments hold. If it fails, the product
is not shippable regardless of feature completeness."

Every attempt here is made as DIRECT SQL, bypassing the application entirely.
That is the point: the edge, API and service layers are each one refactor
away from being gone, and a refactor is not a reviewable event. Only the
database constraint requires a migration to remove.
"""

from __future__ import annotations

import uuid

import psycopg
import pytest

from tests.conftest import insert_event

pytestmark = pytest.mark.filterwarnings("error")


@pytest.mark.active_rule("BR-005")
def test_db1_verified_event_without_reviewer_is_rejected(db, seed):
    """DB-1: insert a verified event with a null reviewer_id.

    BR-005 — every record carries its reviewer. An application-layer check
    is insufficient because a future API could bypass it.
    """
    with pytest.raises(psycopg.errors.CheckViolation) as exc:
        insert_event(
            db, seed,
            status="accepted",
            decided_at="2026-08-12T10:00:00+00:00",
            decision_type="accept",
        )
    assert "chk_decided_requires_reviewer" in str(exc.value)


@pytest.mark.active_rule("BR-004")
def test_db2_unverified_event_with_reviewer_is_rejected(db, seed):
    """DB-2: insert an UNVERIFIED event that already carries a reviewer.

    This is the direction that matters most. It forbids pre-filled
    attribution — a row prepared with a reviewer already attached and then
    flipped to 'accepted' by something that is not the decision path.
    Without it, BR-004 becomes a convention rather than a guarantee.
    """
    with pytest.raises(psycopg.errors.CheckViolation) as exc:
        insert_event(db, seed, status="unverified", reviewer_id=seed["user"])
    assert "chk_decided_requires_reviewer" in str(exc.value)


@pytest.mark.active_rule("BR-004")
def test_decided_event_with_full_attribution_is_accepted(db, seed):
    """The constraint must permit the legitimate case.

    A constraint that rejects everything passes every violation test and
    breaks the product. Both directions are asserted deliberately.
    """
    event_id = insert_event(
        db, seed,
        status="accepted",
        reviewer_id=seed["user"],
        decided_at="2026-08-12T10:00:00+00:00",
        decision_type="accept",
    )
    row = db.execute(
        "SELECT status, reviewer_id FROM events WHERE id = %s", (event_id,)
    ).fetchone()
    assert row == ("accepted", seed["user"])


@pytest.mark.proposed_rule("BR-V-01")
def test_db5_decided_event_cannot_be_reopened(db, seed):
    """DB-5: return a decided event to 'unverified'.

    RULE_BOOK BR-V-01 is PROPOSED and carries no force until ratified, so
    this test is informational rather than release-blocking. The enforcement
    is built because DATABASE.md specifies it.
    """
    event_id = insert_event(
        db, seed,
        status="accepted",
        reviewer_id=seed["user"],
        decided_at="2026-08-12T10:00:00+00:00",
        decision_type="accept",
    )
    with pytest.raises(psycopg.errors.RestrictViolation) as exc:
        db.execute("UPDATE events SET status = 'unverified' WHERE id = %s", (event_id,))
    assert "cannot be reopened" in str(exc.value)


@pytest.mark.coherence
def test_db20_expired_event_cannot_carry_a_reviewer(db, seed):
    """DB-20: an expired event asserting a decision that never happened.

    Expiry is the terminal state of a candidate NO reviewer reached in time
    (RULE_BOOK 3.1). TRD 9.5 leaves this branch of the CHECK bare, which
    permits an expired row to carry reviewer, timestamp and decision type —
    amendment AMD-DB-04, tightened in migration 0005.
    """
    with pytest.raises(psycopg.errors.CheckViolation) as exc:
        insert_event(
            db, seed,
            status="expired",
            reviewer_id=seed["user"],
            decided_at="2026-08-12T10:00:00+00:00",
            decision_type="accept",
        )
    assert "chk_decided_requires_reviewer" in str(exc.value)


@pytest.mark.coherence
def test_rejection_without_a_reason_is_rejected(db, seed):
    """FR-043. A rejection with no stated reason is not reviewable, and the
    rejection log is what makes the system's own error rate visible (BR-R-03).
    """
    with pytest.raises(psycopg.errors.CheckViolation) as exc:
        insert_event(
            db, seed,
            status="rejected",
            reviewer_id=seed["user"],
            decided_at="2026-08-12T10:00:00+00:00",
            decision_type="reject",
        )
    assert "chk_rejection_has_reason" in str(exc.value)


@pytest.mark.active_rule("BR-004")
def test_no_auto_accepted_status_exists(db, seed):
    """There is no auto_accepted state and no escalated state.

    TRD 11.2: "Their absence is the architecture, not an omission." The
    status set is VARCHAR + CHECK rather than a native ENUM precisely so
    that adding a value appears in a migration diff as an unmistakable
    rewrite of a named constraint (DATABASE.md 6.5).
    """
    with pytest.raises(psycopg.errors.CheckViolation) as exc:
        insert_event(db, seed, status="auto_accepted")

    # Two constraints reject it and PostgreSQL reports whichever it reaches
    # first: chk_status_valid because the value is not in the allowed set,
    # and chk_decided_requires_reviewer because an unknown status matches
    # none of its three branches. Defence in depth inside a single layer.
    assert any(
        name in str(exc.value)
        for name in ("chk_status_valid", "chk_decided_requires_reviewer")
    )


@pytest.mark.coherence
def test_duplicate_event_id_is_rejected(db, seed):
    """DB-10: the idempotency key.

    At-least-once delivery from the edge outbox becomes exactly-once effect
    at ingest. The publisher may retry a batch it already delivered.
    """
    shared = uuid.uuid4()
    insert_event(db, seed, event_id=shared)
    with pytest.raises(psycopg.errors.UniqueViolation) as exc:
        insert_event(db, seed, event_id=shared)
    assert "uq_events_event_id" in str(exc.value)
