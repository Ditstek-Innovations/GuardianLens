"""Decision immutability, site-consistency, updated_at.

Revision ID: 0008
Revises: 0007

*** TIER T3 — GOVERNANCE.md 8.2. ***
Rules affected: BR-AU-02 (ABSOLUTE), BR-V-01 (PROPOSED).

trg_events_immutable_decision is what makes "a decided event is immutable"
true against any caller, including direct SQL. A reviewer error is addressed
by a NEW correcting record referencing the original; the original remains,
because an audit trail that can be edited is not an audit trail (TRD 11.4).

trg_events_site_consistency is the trigger TRD 8.3 promises and never
defines. It derives site_id when absent and rejects it when it contradicts
the camera — deriving silently over a supplied-but-wrong value would hide a
caller defect, whereas rejecting surfaces one (AMD-DB-05).
"""

from __future__ import annotations

from alembic import op

revision: str = "0008"
down_revision: str | None = "0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE OR REPLACE FUNCTION fn_events_immutable_decision()
        RETURNS TRIGGER AS $$
        BEGIN
            IF OLD.reviewer_id IS NOT NULL
               AND NEW.reviewer_id IS DISTINCT FROM OLD.reviewer_id THEN
                RAISE EXCEPTION
                    'reviewer_id is immutable once set (BR-AU-02)'
                    USING ERRCODE = 'restrict_violation';
            END IF;

            IF OLD.decided_at IS NOT NULL
               AND NEW.decided_at IS DISTINCT FROM OLD.decided_at THEN
                RAISE EXCEPTION
                    'decided_at is immutable once set (BR-AU-02)'
                    USING ERRCODE = 'restrict_violation';
            END IF;

            IF OLD.decision_type IS NOT NULL
               AND NEW.decision_type IS DISTINCT FROM OLD.decision_type THEN
                RAISE EXCEPTION
                    'decision_type is immutable once set (BR-AU-02)'
                    USING ERRCODE = 'restrict_violation';
            END IF;

            -- A terminal event may never return to unverified (BR-V-01).
            -- chk_decided_requires_reviewer already catches this today, but
            -- only incidentally: the guarantee would be a side effect of a
            -- constraint written for a different purpose. Stated explicitly
            -- so it survives a future edit to that CHECK.
            IF OLD.status <> 'unverified' AND NEW.status = 'unverified' THEN
                RAISE EXCEPTION
                    'a decided event cannot be reopened (BR-V-01)'
                    USING ERRCODE = 'restrict_violation';
            END IF;

            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
        """
    )

    op.execute(
        """
        CREATE TRIGGER trg_events_immutable_decision
            BEFORE UPDATE ON events
            FOR EACH ROW EXECUTE FUNCTION fn_events_immutable_decision()
        """
    )

    op.execute(
        """
        CREATE OR REPLACE FUNCTION fn_events_site_consistency()
        RETURNS TRIGGER AS $$
        DECLARE
            v_camera_site UUID;
        BEGIN
            SELECT site_id INTO v_camera_site
              FROM cameras WHERE id = NEW.camera_id;

            IF v_camera_site IS NULL THEN
                RAISE EXCEPTION 'unknown camera_id %', NEW.camera_id
                    USING ERRCODE = 'foreign_key_violation';
            END IF;

            IF NEW.site_id IS NULL THEN
                NEW.site_id := v_camera_site;
            ELSIF NEW.site_id IS DISTINCT FROM v_camera_site THEN
                RAISE EXCEPTION
                    'events.site_id (%) does not match cameras.site_id (%)',
                    NEW.site_id, v_camera_site
                    USING ERRCODE = 'check_violation';
            END IF;

            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
        """
    )

    op.execute(
        """
        CREATE TRIGGER trg_events_site_consistency
            BEFORE INSERT OR UPDATE OF site_id, camera_id ON events
            FOR EACH ROW EXECUTE FUNCTION fn_events_site_consistency()
        """
    )

    # updated_at is set by the database, not trusted from the caller.
    op.execute(
        """
        CREATE OR REPLACE FUNCTION fn_touch_updated_at()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at := now();
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
        """
    )

    for table in ("sites", "cameras", "zones", "detection_rules", "users"):
        op.execute(
            f"""
            CREATE TRIGGER trg_{table}_touch_updated_at
                BEFORE UPDATE ON {table}
                FOR EACH ROW EXECUTE FUNCTION fn_touch_updated_at()
            """
        )


def downgrade() -> None:
    for table in ("sites", "cameras", "zones", "detection_rules", "users"):
        op.execute(f"DROP TRIGGER IF EXISTS trg_{table}_touch_updated_at ON {table}")
    op.execute("DROP FUNCTION IF EXISTS fn_touch_updated_at()")
    op.execute("DROP TRIGGER IF EXISTS trg_events_site_consistency ON events")
    op.execute("DROP FUNCTION IF EXISTS fn_events_site_consistency()")
    op.execute("DROP TRIGGER IF EXISTS trg_events_immutable_decision ON events")
    op.execute("DROP FUNCTION IF EXISTS fn_events_immutable_decision()")
