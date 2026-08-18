"""DB-15, DB-16 — the rules enforced by absence.

DATABASE.md 4: four ABSOLUTE rules are guaranteed by things that do not
exist, and absence decays silently. These are the strongest tests in the
suite because the statements they attempt CANNOT BE WRITTEN — not "are
rejected", but "have no object to refer to".

    "That is the strongest form of enforcement in this document, and it is
     why section 4 (the negative schema) is a section rather than a
     footnote."
"""

from __future__ import annotations

import psycopg
import pytest

# Columns and tables from DATABASE.md 4.1. A migration adding any of these
# is an ABSOLUTE rule violation, whatever the stated intent.
FORBIDDEN_TABLES = (
    "persons", "workers", "subjects", "individuals", "identities",
    "face_embeddings", "tracks", "activity_metrics", "productivity_scores",
    "hr_integrations", "disciplinary_actions", "outbound_webhooks",
    "audio_clips", "video_clips",
)

FORBIDDEN_COLUMN_FRAGMENTS = (
    "person", "worker", "biometric", "face_embedding", "gait",
    "track_id", "reid", "productivity", "idle_time", "work_rate",
    "disciplinary", "hr_case", "webhook_url", "audio", "video",
)


@pytest.mark.active_rule("BR-006")
def test_db15_no_relation_can_grant_a_role_to_an_agent(db):
    """DB-15: grant a role to an agent principal.

    BR-S-02: a fully compromised edge agent cannot verify an event. Not
    because a check refuses it — because `user_roles.user_id` references
    `users`, `agents` is a separate table, and no column exists through
    which the grant could be expressed.

    Removing this guarantee would require dropping and rebuilding the
    authorisation model, not changing a check.
    """
    columns = {
        row[0]
        for row in db.execute(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_name = 'user_roles'"
        ).fetchall()
    }
    assert "agent_id" not in columns
    assert columns == {"user_id", "role_id", "site_id", "granted_by", "granted_at"}

    # The foreign key targets users, and only users.
    targets = {
        row[0]
        for row in db.execute(
            """
            SELECT ccu.table_name
              FROM information_schema.table_constraints tc
              JOIN information_schema.constraint_column_usage ccu
                ON ccu.constraint_name = tc.constraint_name
             WHERE tc.table_name = 'user_roles'
               AND tc.constraint_type = 'FOREIGN KEY'
            """
        ).fetchall()
    }
    assert "agents" not in targets

    # And the statement itself cannot be written.
    with pytest.raises(psycopg.errors.UndefinedColumn):
        db.execute("INSERT INTO user_roles (agent_id, role_id) VALUES (NULL, NULL)")


@pytest.mark.active_rule("BR-002")
def test_db16_no_per_person_measure_column_exists(db):
    """DB-16: query a per-person activity aggregate.

    BR-002 forbids any measure of an individual's activity level, idle time,
    presence duration, work rate or output — at any horizon, including
    future analytics. It is enforced by the absence of a person concept, not
    by a filter, because a filter can be forgotten.
    """
    rows = db.execute(
        """
        SELECT table_name, column_name
          FROM information_schema.columns
         WHERE table_schema = current_schema()
        """
    ).fetchall()

    offenders = [
        f"{table}.{column}"
        for table, column in rows
        for fragment in FORBIDDEN_COLUMN_FRAGMENTS
        if fragment in column.lower()
    ]
    assert not offenders, (
        f"columns matching the DATABASE.md 4.1 prohibition list: {offenders}"
    )


@pytest.mark.active_rule("BR-006")
def test_no_forbidden_table_exists(db):
    """No entity representing a person in frame, at any horizon.

    RULE_BOOK 3.2 contains no *worker is identified* fact type, so a feature
    requiring one cannot be expressed in the product's own vocabulary.
    """
    present = {
        row[0]
        for row in db.execute(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema = current_schema()"
        ).fetchall()
    }
    assert not (present & set(FORBIDDEN_TABLES))


@pytest.mark.active_rule("BR-003")
def test_no_outbound_consequence_column_exists(db):
    """BR-003: no code path from a record to any consequence for a worker.

    There is no integration layer to HR, performance or disciplinary
    systems. Not disabled — absent. A configurable `webhook_url` on sites or
    detection_rules would reintroduce it in one column.
    """
    columns = {
        f"{t}.{c}".lower()
        for t, c in db.execute(
            "SELECT table_name, column_name FROM information_schema.columns "
            "WHERE table_schema = current_schema()"
        ).fetchall()
    }
    for banned in ("webhook", "hr_", "disciplinary", "escalation", "notified_manager"):
        assert not [c for c in columns if banned in c], f"found {banned!r}"


@pytest.mark.tenancy
def test_no_tenant_id_column_on_any_business_table(db):
    """DATABASE.md 2.1 — the column that deliberately does not exist.

    In a silo model the database IS the tenant scope, so a tenant_id column
    would be either always the same (useless) or sometimes different
    (evidence of the contamination it was meant to prevent). Worse, its
    presence invites a filter, and a filter invites a forgotten filter —
    precisely the failure class ADR-016 was adopted to eliminate.

    The tenant is asserted once per connection, not once per row.
    """
    offenders = db.execute(
        """
        SELECT table_name FROM information_schema.columns
         WHERE table_schema = current_schema()
           AND column_name = 'tenant_id'
           AND table_name <> 'tenant_identity'
        """
    ).fetchall()
    assert not offenders, f"tenant_id found on: {[r[0] for r in offenders]}"
