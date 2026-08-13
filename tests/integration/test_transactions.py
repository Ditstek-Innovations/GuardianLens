"""Transaction semantics that the rules depend on.

TRD 19.3 lists these as integration tests. They are testable at the data
layer today, before the service layer exists, because the guarantees are
transactional rather than procedural — and a guarantee that only holds
because the service happens to be written correctly is not a guarantee.
"""

from __future__ import annotations

import uuid
from collections.abc import Iterator

import psycopg
import pytest

from guardian_lens.db.urls import psycopg_url
from tests.conftest import insert_event


@pytest.fixture
def committed(tenant_db_url: str) -> Iterator[tuple[psycopg.Connection, dict]]:
    """A COMMITTED seed graph plus its connection, for two-session tests.

    Concurrency cannot be observed inside one rolled-back transaction — the
    second session must be able to see what the first wrote. So this fixture
    commits, and unwinds in reverse dependency order afterwards.

    Note what it cannot unwind: audit_log rows. The append-only trigger
    refuses, which is the trigger working. Nothing here writes any.
    """
    conn = psycopg.connect(psycopg_url(tenant_db_url))
    ids = {k: uuid.uuid4() for k in ("site", "camera", "zone", "rule", "agent",
                                     "model", "user")}
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO users (id, email, full_name, password_hash) "
            "VALUES (%s, %s, 'Concurrent Reviewer', 'x')",
            (ids["user"], f"c+{ids['user']}@example.test"),
        )
        cur.execute("INSERT INTO sites (id, name, timezone) "
                    "VALUES (%s, 'Concurrency Site', 'UTC')", (ids["site"],))
        cur.execute(
            "INSERT INTO cameras (id, site_id, name, stream_url_encrypted, "
            "stream_url_key_id) VALUES (%s, %s, 'cam', %s, 'k')",
            (ids["camera"], ids["site"], b"\x00ct"),
        )
        cur.execute("INSERT INTO zones (id, camera_id, name, polygon) "
                    "VALUES (%s, %s, 'z', '[[0,0],[1,0],[1,1]]')",
                    (ids["zone"], ids["camera"]))
        cur.execute(
            """
            INSERT INTO detection_rules (id, zone_id, rule_type,
                confidence_threshold, debounce_seconds, human_readable,
                created_by, is_active, activated_by, activated_at)
            VALUES (%s, %s, 'ppe_helmet', 0.5, 30, 'r', %s, TRUE, %s, now())
            """,
            (ids["rule"], ids["zone"], ids["user"], ids["user"]),
        )
        cur.execute("INSERT INTO agents (id, site_id, name, credential_hash) "
                    "VALUES (%s, %s, 'a', 'x')", (ids["agent"], ids["site"]))
        cur.execute(
            "INSERT INTO model_versions (id, version, artefact_hash, classes) "
            "VALUES (%s, %s, 'sha256:x', '[]')",
            (ids["model"], f"c-{ids['model'].hex[:8]}"),
        )
    conn.commit()
    try:
        yield conn, ids
    finally:
        conn.rollback()
        with conn.cursor() as cur:
            for stmt, key in (
                ("DELETE FROM events WHERE site_id = %s", "site"),
                ("DELETE FROM detection_rules WHERE id = %s", "rule"),
                ("DELETE FROM zones WHERE id = %s", "zone"),
                ("DELETE FROM cameras WHERE id = %s", "camera"),
                ("DELETE FROM agents WHERE id = %s", "agent"),
                ("DELETE FROM model_versions WHERE id = %s", "model"),
                ("DELETE FROM sites WHERE id = %s", "site"),
                ("DELETE FROM users WHERE id = %s", "user"),
            ):
                cur.execute(stmt, (ids[key],))
        conn.commit()
        conn.close()


@pytest.mark.active_rule("BR-AU-03")
def test_a_decision_that_cannot_be_audited_does_not_exist(db, seed):
    """BR-AU-03 / TRD 11.3 transaction rule.

    "Write the decision, retry the audit later" is the obvious optimisation
    and it is prohibited. The failure mode of the alternative is a verified
    record with no provenance — precisely the artefact the product exists to
    prevent.
    """
    event_id = insert_event(db, seed)

    # A savepoint, not a commit: db.transaction() nests inside the fixture's
    # open transaction, so nothing this test writes outlives it.
    with pytest.raises(psycopg.errors.CheckViolation):
        with db.transaction():
            db.execute(
                """
                UPDATE events
                   SET status = 'accepted', reviewer_id = %s,
                       decided_at = now(), decision_type = 'accept'
                 WHERE id = %s
                """,
                (seed["user"], event_id),
            )
            # The audit write fails: no actor, and not a system action.
            db.execute(
                "INSERT INTO audit_log (action, entity_type, entity_id) "
                "VALUES ('event.decided', 'events', %s)",
                (event_id,),
            )

    status = db.execute(
        "SELECT status, reviewer_id FROM events WHERE id = %s", (event_id,)
    ).fetchone()
    assert status == ("unverified", None), "the decision survived an unaudited write"


@pytest.mark.active_rule("BR-005")
def test_decision_and_audit_commit_together(db, seed):
    """The legitimate case, so the test above is not passing for the wrong
    reason."""
    event_id = insert_event(db, seed)
    with db.transaction():
        db.execute(
            """
            UPDATE events SET status = 'accepted', reviewer_id = %s,
                              decided_at = now(), decision_type = 'accept'
             WHERE id = %s
            """,
            (seed["user"], event_id),
        )
        db.execute(
            """
            INSERT INTO audit_log (actor_user_id, action, entity_type, entity_id,
                                   before_state, after_state)
            VALUES (%s, 'event.decided', 'events', %s,
                    '{"status":"unverified"}', '{"status":"accepted"}')
            """,
            (seed["user"], event_id),
        )

    assert db.execute(
        "SELECT count(*) FROM audit_log WHERE entity_id = %s", (event_id,)
    ).fetchone()[0] == 1


@pytest.mark.coherence
def test_concurrent_decisions_on_one_event_leave_exactly_one_winner(
    committed, tenant_db_url
):
    """TRD 19.3: "Concurrent decisions on one event — exactly one succeeds."

    Optimistic concurrency on the version column. Two reviewers open the
    same candidate; the second must be told a decision already exists rather
    than silently overwriting the first reviewer's attribution.
    """
    conn, seed = committed
    event_id = insert_event(conn, seed)
    conn.commit()

    sql = """
        UPDATE events
           SET status = 'accepted', reviewer_id = %s, decided_at = now(),
               decision_type = 'accept', version = version + 1
         WHERE id = %s AND version = %s
    """

    winners = 0
    with psycopg.connect(psycopg_url(tenant_db_url)) as a, \
         psycopg.connect(psycopg_url(tenant_db_url)) as b:
        # Not `conn` — that name belongs to the fixture connection, and
        # psycopg closes a connection on __exit__.
        for session in (a, b):
            with session.cursor() as cur:
                cur.execute(sql, (seed["user"], event_id, 1))
                winners += cur.rowcount
            session.commit()

    assert winners == 1, "both decisions were applied to one event"

    row = conn.execute(
        "SELECT status, version FROM events WHERE id = %s", (event_id,)
    ).fetchone()
    assert row == ("accepted", 2)


@pytest.mark.coherence
def test_a_stale_version_updates_nothing(committed):
    """The second reviewer's request carries the version they were shown.
    A stale one matches no row, which is what the service turns into a 409
    rather than a silent overwrite."""
    conn, seed = committed
    event_id = insert_event(conn, seed)
    conn.commit()

    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE events SET status = 'accepted', reviewer_id = %s,
                              decided_at = now(), decision_type = 'accept'
             WHERE id = %s AND version = 99
            """,
            (seed["user"], event_id),
        )
        assert cur.rowcount == 0
    conn.rollback()
