"""DB-3, DB-4, DB-6, DB-7, DB-8 — the audit trail.

The audit trail is a database table, not a log file (TRD 15.5). Files
rotate, truncate and get lost; the audit trail is a product feature.

What these tests do NOT establish is protection against a principal holding
database administrative rights, who can DISABLE TRIGGER, modify rows and
re-enable. Against that the current design offers deterrence, not evidence —
threat T-12, risk R-1. ADR-015 is the [V1] answer.
"""

from __future__ import annotations

import psycopg
import pytest

from tests.conftest import insert_event


def _write_audit_entry(db, seed) -> None:
    db.execute(
        """
        INSERT INTO audit_log (actor_user_id, action, entity_type, entity_id,
                               after_state)
        VALUES (%s, 'event.decided', 'events', %s, '{"status":"accepted"}')
        """,
        (seed["user"], seed["site"]),
    )


@pytest.mark.active_rule("BR-AU-02")
def test_db3_reviewer_id_is_immutable_after_decision(db, seed):
    """DB-3: rewrite the reviewer on a decided event.

    Overriding attribution would defeat BR-005 entirely — the record would
    name someone who did not make the judgement.
    """
    event_id = insert_event(
        db, seed,
        status="accepted",
        reviewer_id=seed["user"],
        decided_at="2026-08-12T10:00:00+00:00",
        decision_type="accept",
    )
    other = db.execute(
        "INSERT INTO users (email, full_name, password_hash) "
        "VALUES ('other@example.test', 'Other', 'x') RETURNING id"
    ).fetchone()[0]

    with pytest.raises(psycopg.errors.RestrictViolation) as exc:
        db.execute("UPDATE events SET reviewer_id = %s WHERE id = %s",
                   (other, event_id))
    assert "reviewer_id is immutable" in str(exc.value)


@pytest.mark.active_rule("BR-AU-02")
def test_db4_decided_at_is_immutable_after_decision(db, seed):
    """DB-4: move the decision timestamp."""
    event_id = insert_event(
        db, seed,
        status="accepted",
        reviewer_id=seed["user"],
        decided_at="2026-08-12T10:00:00+00:00",
        decision_type="accept",
    )
    with pytest.raises(psycopg.errors.RestrictViolation) as exc:
        db.execute(
            "UPDATE events SET decided_at = '2020-01-01T00:00:00+00:00' "
            "WHERE id = %s",
            (event_id,),
        )
    assert "decided_at is immutable" in str(exc.value)


@pytest.mark.active_rule("BR-AU-01")
def test_db6_audit_log_update_is_rejected(db, seed):
    """DB-6: UPDATE the audit log."""
    _write_audit_entry(db, seed)
    with pytest.raises(psycopg.errors.RestrictViolation) as exc:
        db.execute("UPDATE audit_log SET action = 'tampered'")
    assert "append-only" in str(exc.value)


@pytest.mark.active_rule("BR-AU-01")
def test_db7_audit_log_delete_is_rejected(db, seed):
    """DB-7: DELETE from the audit log."""
    _write_audit_entry(db, seed)
    with pytest.raises(psycopg.errors.RestrictViolation) as exc:
        db.execute("DELETE FROM audit_log")
    assert "append-only" in str(exc.value)


@pytest.mark.active_rule("BR-AU-01")
def test_db8_audit_log_truncate_is_rejected(db, seed):
    """DB-8: TRUNCATE the audit log.

    *** The case the existing suite does not cover. ***

    A row-level BEFORE UPDATE OR DELETE trigger — which is what TRD 9.11
    specifies — does NOT fire on TRUNCATE. Without the statement-level
    trigger added in migration 0006, DB-6 and DB-7 would both pass while
    `TRUNCATE audit_log` erased the entire trail. Amendment AMD-DB-16.
    """
    _write_audit_entry(db, seed)
    with pytest.raises(psycopg.errors.RestrictViolation) as exc:
        db.execute("TRUNCATE audit_log")
    assert "append-only" in str(exc.value)


@pytest.mark.active_rule("BR-010")
def test_audit_entry_without_an_actor_is_rejected(db):
    """An audit entry can never have an unexplained absence of actor.

    A system action is permitted, but must say so: the action name carries
    the 'system.' prefix, so "nobody did this" is an assertion rather than
    an omission.
    """
    with pytest.raises(psycopg.errors.CheckViolation) as exc:
        db.execute(
            "INSERT INTO audit_log (action, entity_type) "
            "VALUES ('event.decided', 'events')"
        )
    assert "chk_audit_has_actor" in str(exc.value)


@pytest.mark.active_rule("BR-010")
def test_system_action_without_an_actor_is_accepted(db):
    """The legitimate case: a system action, explicitly labelled.

    Asserts on the inserted row itself, not a global count: other suites
    legitimately commit system.* entries (e.g. system.user.signed_up), and
    the append-only trigger means they can never be cleaned up — which is
    the trigger doing its job, not a fixture defect.
    """
    row_id = db.execute(
        "INSERT INTO audit_log (action, entity_type) "
        "VALUES ('system.retention.deleted', 'events') RETURNING id"
    ).fetchone()[0]
    assert row_id is not None


@pytest.mark.active_rule("BR-010")
def test_audit_entry_cannot_name_both_a_user_and_an_agent(db, seed):
    """Exactly one actor. An entry naming both attributes an act to two
    principals, one of which did not perform it."""
    with pytest.raises(psycopg.errors.CheckViolation):
        db.execute(
            """
            INSERT INTO audit_log (actor_user_id, actor_agent_id, action,
                                   entity_type)
            VALUES (%s, %s, 'event.decided', 'events')
            """,
            (seed["user"], seed["agent"]),
        )
