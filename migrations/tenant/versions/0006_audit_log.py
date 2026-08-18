"""Append-only audit log.

Revision ID: 0006
Revises: 0005

*** TIER T3 — GOVERNANCE.md 8.2. ***
Rules affected: BR-AU-01 (ABSOLUTE), BR-010 (STRONG).

The audit trail is a database table, not a log file — TRD 15.5. Files
rotate, truncate and get lost; the audit trail is a product feature rather
than an operational convenience.

The append-only guarantee holds twice: AuditRepository exposes no update or
delete method at all, and the triggers below reject the operation whatever
the caller. Only the second survives a direct database connection.

*** The TRUNCATE trigger is not a detail. ***
A row-level BEFORE UPDATE OR DELETE trigger — which is what TRD 9.11
specifies — does NOT fire on TRUNCATE. The bypass suite tests UPDATE and
DELETE and would pass green while `TRUNCATE audit_log` erased the entire
trail. See AMD-DB-16 and bypass case DB-8.

What this does NOT defend against is a principal holding database
administrative rights, who can DISABLE TRIGGER, modify rows and re-enable.
Against that, the current design offers deterrence, not evidence — threat
T-12, risk R-1. ADR-015 (hash chain plus signed off-box Merkle checkpoints)
is the [V1] answer and is deliberately not in this revision.
"""

from __future__ import annotations

from alembic import op

revision: str = "0006"
down_revision: str | None = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE audit_log (
            id             BIGSERIAL   PRIMARY KEY,
            actor_user_id  UUID        REFERENCES users(id) ON DELETE RESTRICT,
            actor_agent_id UUID        REFERENCES agents(id) ON DELETE RESTRICT,
            action         VARCHAR(64) NOT NULL,
            entity_type    VARCHAR(50) NOT NULL,
            entity_id      UUID,
            -- Not every auditable entity has a UUID key. user_roles has a
            -- composite key, and granting or revoking a role is exactly the
            -- scope change BR-010 requires to be logged and attributable —
            -- AMD-DB-13.
            entity_key     TEXT,
            -- FIELD ALLOWLIST PER ENTITY TYPE, never a whole row. A naive
            -- "log the whole row" implementation would copy
            -- cameras.stream_url_encrypted into a JSONB column with none of
            -- that column's protections, turning the audit log into the
            -- credential store's weakest replica (DATABASE.md 8.3).
            before_state   JSONB,
            after_state    JSONB,
            ip_address     INET,
            occurred_at    TIMESTAMPTZ NOT NULL DEFAULT now(),

            CONSTRAINT chk_audit_has_actor CHECK (
                (actor_user_id IS NOT NULL AND actor_agent_id IS NULL)
                OR (actor_user_id IS NULL AND actor_agent_id IS NOT NULL)
                OR (actor_user_id IS NULL AND actor_agent_id IS NULL
                    AND action LIKE 'system.%')
            )
        )
        """
    )

    op.execute(
        """
        CREATE OR REPLACE FUNCTION fn_audit_append_only()
        RETURNS TRIGGER AS $$
        BEGIN
            RAISE EXCEPTION
                'audit_log is append-only (BR-AU-01); % rejected', TG_OP
                USING ERRCODE = 'restrict_violation';
        END;
        $$ LANGUAGE plpgsql
        """
    )

    op.execute(
        """
        CREATE TRIGGER trg_audit_append_only
            BEFORE UPDATE OR DELETE ON audit_log
            FOR EACH ROW EXECUTE FUNCTION fn_audit_append_only()
        """
    )

    # Row-level triggers do not fire on TRUNCATE. This one does.
    op.execute(
        """
        CREATE TRIGGER trg_audit_no_truncate
            BEFORE TRUNCATE ON audit_log
            FOR EACH STATEMENT EXECUTE FUNCTION fn_audit_append_only()
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trg_audit_no_truncate ON audit_log")
    op.execute("DROP TRIGGER IF EXISTS trg_audit_append_only ON audit_log")
    op.execute("DROP FUNCTION IF EXISTS fn_audit_append_only()")
    op.execute("DROP TABLE IF EXISTS audit_log")
