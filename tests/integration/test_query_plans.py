"""The partial indexes actually serve the queries they were created for.

DATABASE.md 7.1 names ten queries and 7.2 creates an index for each. An
index without a query is speculative cost; an index the planner ignores is
worse, because it looks like coverage. These tests check the claim.

What they establish: the index MATCHES THE SHAPE of the query. What they
cannot establish is the plan at production volume, because the volume is
[OPEN — PRD OQ-4] and inventing one would be inventing a figure.
"""

from __future__ import annotations

import os
import uuid
from collections.abc import Iterator

import psycopg
import pytest

from guardian_lens.db.provisioning import deprovision, provision
from guardian_lens.db.urls import psycopg_url, tenant_url

ROWS = 2000


@pytest.fixture(scope="module")
def populated(request) -> Iterator[psycopg.Connection]:
    """A tenant with enough rows that the planner has a real choice."""
    control = os.environ.get("GL_CONTROL_DB_URL")
    base = os.environ.get("GL_TENANT_DB_URL")
    if not control or not base:
        pytest.skip("database URLs not set")

    slug = f"plans_{uuid.uuid4().hex[:8]}"
    provision(slug, "Query plans", base_url=base, control_url=control)
    conn = psycopg.connect(psycopg_url(tenant_url(base, slug)))

    ids = {k: uuid.uuid4() for k in ("site", "camera", "zone", "rule", "agent",
                                     "model", "user")}
    with conn.cursor() as cur:
        cur.execute("INSERT INTO users (id, email, full_name, password_hash) "
                    "VALUES (%s, 'p@example.test', 'P', 'x')", (ids["user"],))
        cur.execute("INSERT INTO sites (id, name, timezone) "
                    "VALUES (%s, 'S', 'UTC')", (ids["site"],))
        cur.execute("INSERT INTO cameras (id, site_id, name, "
                    "stream_url_encrypted, stream_url_key_id) "
                    "VALUES (%s, %s, 'c', %s, 'k')",
                    (ids["camera"], ids["site"], b"\x00"))
        cur.execute("INSERT INTO zones (id, camera_id, name, polygon) "
                    "VALUES (%s, %s, 'z', '[[0,0]]')",
                    (ids["zone"], ids["camera"]))
        cur.execute(
            "INSERT INTO detection_rules (id, zone_id, rule_type, "
            "confidence_threshold, debounce_seconds, human_readable, "
            "created_by) VALUES (%s, %s, 'ppe_helmet', 0.5, 30, 'r', %s)",
            (ids["rule"], ids["zone"], ids["user"]),
        )
        cur.execute("INSERT INTO agents (id, site_id, name, credential_hash) "
                    "VALUES (%s, %s, 'a', 'x')", (ids["agent"], ids["site"]))
        cur.execute("INSERT INTO model_versions (id, version, artefact_hash, "
                    "classes) VALUES (%s, '1.0.0', 'sha', '[]')", (ids["model"],))

        # 95% decided, 5% unverified: the shape the partial queue index is
        # designed for — a small live backlog against a large history.
        cur.executemany(
            """
            INSERT INTO events (event_id, site_id, camera_id, zone_id, rule_id,
                rule_snapshot, agent_id, model_version_id, confidence,
                occurred_at, evidence_state, status, reviewer_id, decided_at,
                decision_type)
            VALUES (%s, %s, %s, %s, %s, '{}', %s, %s, 0.9,
                    now() - (%s * interval '1 minute'), 'none',
                    %s, %s, %s, %s)
            """,
            [
                (
                    uuid.uuid4(), ids["site"], ids["camera"], ids["zone"],
                    ids["rule"], ids["agent"], ids["model"], i,
                    "unverified" if i % 20 == 0 else "accepted",
                    None if i % 20 == 0 else ids["user"],
                    None if i % 20 == 0 else "2026-08-12T10:00:00+00:00",
                    None if i % 20 == 0 else "accept",
                )
                for i in range(ROWS)
            ],
        )
    conn.commit()
    conn.execute("ANALYZE events")
    conn.commit()
    try:
        yield conn
    finally:
        conn.close()
        deprovision(slug, base_url=base, control_url=control)


def _plan(conn: psycopg.Connection, sql: str, params: tuple) -> str:
    rows = conn.execute(f"EXPLAIN {sql}", params).fetchall()
    return "\n".join(r[0] for r in rows)


@pytest.mark.coherence
def test_q1_the_review_queue_uses_the_partial_index(populated):
    """Q-1, the hottest read path and the one a reviewer feels directly.

    Partial on status='unverified', so its size tracks the undisposed
    backlog rather than total history — queue performance stays flat as a
    site accumulates years of verified records.
    """
    site = populated.execute("SELECT id FROM sites LIMIT 1").fetchone()[0]
    plan = _plan(
        populated,
        """
        SELECT id, occurred_at FROM events
         WHERE status = 'unverified' AND site_id = %s
         ORDER BY occurred_at DESC LIMIT 50
        """,
        (site,),
    )
    assert "idx_events_queue" in plan, plan
    assert "Seq Scan" not in plan, plan


@pytest.mark.active_rule("BR-R-01")
def test_q3_reporting_uses_the_verified_only_partial_index(populated):
    """Q-3. Also partial: every report query filters the verified statuses
    at the repository layer anyway (BR-R-01), so a full index would carry
    rows no report can ever read.

    The window is deliberately narrow. A report spanning the whole dataset
    is CORRECTLY a sequential scan — reading 95% of a table via an index is
    slower, and asserting otherwise would be asserting the planner is wrong.
    A shift or a day is the realistic shape (PRD F-9), not a year.
    """
    site = populated.execute("SELECT id FROM sites LIMIT 1").fetchone()[0]
    plan = _plan(
        populated,
        """
        SELECT id FROM events
         WHERE site_id = %s AND status IN ('accepted','corrected')
           AND occurred_at >= now() - interval '2 hours'
         ORDER BY occurred_at DESC
        """,
        (site,),
    )
    assert "idx_events_site_occurred" in plan, plan


@pytest.mark.coherence
def test_a_full_history_report_is_correctly_a_sequential_scan(populated):
    """The counterpart to the test above, stated so nobody 'fixes' it later.

    When a report covers effectively the whole table the planner chooses a
    sequential scan, and it is right to. This is recorded because the
    obvious reaction to seeing Seq Scan in a plan is to add an index, and
    here that would make things slower while looking like an improvement.
    """
    site = populated.execute("SELECT id FROM sites LIMIT 1").fetchone()[0]
    plan = _plan(
        populated,
        """
        SELECT id FROM events
         WHERE site_id = %s AND status IN ('accepted','corrected')
         ORDER BY occurred_at DESC
        """,
        (site,),
    )
    assert "Seq Scan" in plan, plan


@pytest.mark.coherence
def test_the_queue_index_stays_small_relative_to_the_table(populated):
    """The property that makes Q-1 hold as history grows: the partial index
    covers only the backlog. If someone 'simplifies' it by removing the
    WHERE clause, this ratio collapses and the queue slows down years into
    a deployment, long after the change is forgotten."""
    queue_rows, total_rows = populated.execute(
        """
        SELECT (SELECT count(*) FROM events WHERE status = 'unverified'),
               (SELECT count(*) FROM events)
        """
    ).fetchone()
    assert queue_rows * 10 < total_rows

    entries = populated.execute(
        "SELECT reltuples::bigint FROM pg_class WHERE relname = 'idx_events_queue'"
    ).fetchone()[0]
    assert 0 <= entries <= queue_rows * 2, (
        f"idx_events_queue holds ~{entries} entries for {queue_rows} "
        f"unverified rows — it is no longer partial"
    )
