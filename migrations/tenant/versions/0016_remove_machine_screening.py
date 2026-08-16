"""Remove the machine-disposition tier — AMD-RB-05 withdrawn (RULE_BOOK 1.2).

Revision ID: 0016
Revises: 0015

The tier was applied under the pending-amendment convention and withdrawn
by its applier before ratification; BR-004/BR-V-03 stand restored to their
original ABSOLUTE text. This migration removes the mechanism and — the
part that matters — RE-OPENS every Machine-Screened Outcome into the human
queue: removal must not silently disappear a candidate (BR-W-02). Events a
human already decided keep their decision and their historical trace; the
append-only audit log keeps the tier's whole story either way.

DATABASE.md 4.3 — the seven questions:

  1. Adds nothing.
  2. Rewrites chk_status_valid and chk_decided_requires_reviewer BACK to
     their exact 0005 definitions — strictly narrowing; every human branch
     byte-identical throughout.
  3. ON DELETE behaviour: unchanged.
  4. events nullability of the decision columns: unchanged.
  5. audit_log: untouched (history of machine screenings remains, as it
     must — append-only).
  6. Retention/expiry: unchanged.
  7. RULE_BOOK rules affected: BR-004/BR-V-03 restored (1.2); BR-W-02
     honoured by the re-open (no candidate silently discarded).

Rules affected: BR-004, BR-V-03 (both restored), BR-W-02 (honoured).
"""

from __future__ import annotations

from alembic import op

revision: str = "0016"
down_revision: str | None = "0015"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # BR-W-02 — every screened candidate returns to the human queue. The
    # 0008 immutability trigger predates the tier and reads ANY
    # non-unverified -> unverified transition as reopening a decision; a
    # machine_screened row is explicitly NOT a decision (it carries no
    # reviewer), so the trigger is suspended for exactly this statement.
    # Human decisions stay untouchable throughout: the UPDATE's WHERE
    # clause cannot reach them, and the trigger is back before anything
    # else runs.
    op.execute(
        "ALTER TABLE events DISABLE TRIGGER trg_events_immutable_decision"
    )
    op.execute(
        """
        UPDATE events SET status = 'unverified',
                          machine_screened_at = NULL,
                          machine_threshold = NULL
         WHERE status = 'machine_screened'
        """
    )
    op.execute(
        "ALTER TABLE events ENABLE TRIGGER trg_events_immutable_decision"
    )
    op.execute("ALTER TABLE events DROP CONSTRAINT chk_decided_requires_reviewer")
    op.execute(
        """
        ALTER TABLE events ADD CONSTRAINT chk_decided_requires_reviewer CHECK (
            (status = 'unverified'
                AND reviewer_id   IS NULL
                AND decided_at    IS NULL
                AND decision_type IS NULL)
            OR
            (status IN ('accepted','rejected','corrected')
                AND reviewer_id   IS NOT NULL
                AND decided_at    IS NOT NULL
                AND decision_type IS NOT NULL)
            OR
            (status = 'expired'
                AND reviewer_id   IS NULL
                AND decided_at    IS NULL
                AND decision_type IS NULL)
        )
        """
    )
    op.execute("ALTER TABLE events DROP CONSTRAINT chk_status_valid")
    op.execute(
        """
        ALTER TABLE events ADD CONSTRAINT chk_status_valid CHECK (
            status IN ('unverified','accepted','rejected','corrected','expired')
        )
        """
    )
    op.execute("ALTER TABLE events DROP COLUMN IF EXISTS machine_threshold")
    op.execute("ALTER TABLE events DROP COLUMN IF EXISTS machine_screened_at")
    op.execute(
        "ALTER TABLE sites DROP CONSTRAINT IF EXISTS chk_sites_auto_review_threshold"
    )
    op.execute("ALTER TABLE sites DROP COLUMN IF EXISTS auto_review_threshold")
    op.execute("ALTER TABLE sites DROP COLUMN IF EXISTS auto_review_enabled")


def downgrade() -> None:
    # Production is forward-only (DATABASE.md 13.1) and reinstating the
    # tier for real is a rule change first (GOVERNANCE.md 8.4). This
    # exists so the revision is reversible in development and CI — it
    # restores 0015's schema shape, nothing more.
    op.execute(
        """
        ALTER TABLE sites
            ADD COLUMN auto_review_enabled BOOLEAN NOT NULL DEFAULT FALSE,
            ADD COLUMN auto_review_threshold NUMERIC(4,3) NOT NULL DEFAULT 0.800,
            ADD CONSTRAINT chk_sites_auto_review_threshold
                CHECK (auto_review_threshold > 0 AND auto_review_threshold <= 1)
        """
    )
    op.execute(
        """
        ALTER TABLE events
            ADD COLUMN machine_screened_at TIMESTAMPTZ,
            ADD COLUMN machine_threshold NUMERIC(4,3)
        """
    )
    op.execute("ALTER TABLE events DROP CONSTRAINT chk_status_valid")
    op.execute(
        """
        ALTER TABLE events ADD CONSTRAINT chk_status_valid CHECK (
            status IN ('unverified','accepted','rejected','corrected',
                       'expired','machine_screened')
        )
        """
    )
    op.execute("ALTER TABLE events DROP CONSTRAINT chk_decided_requires_reviewer")
    op.execute(
        """
        ALTER TABLE events ADD CONSTRAINT chk_decided_requires_reviewer CHECK (
            (status = 'unverified'
                AND reviewer_id   IS NULL
                AND decided_at    IS NULL
                AND decision_type IS NULL
                AND machine_screened_at IS NULL)
            OR
            (status IN ('accepted','rejected','corrected')
                AND reviewer_id   IS NOT NULL
                AND decided_at    IS NOT NULL
                AND decision_type IS NOT NULL)
            OR
            (status = 'expired'
                AND reviewer_id   IS NULL
                AND decided_at    IS NULL
                AND decision_type IS NULL
                AND machine_screened_at IS NULL)
            OR
            (status = 'machine_screened'
                AND reviewer_id   IS NULL
                AND decided_at    IS NULL
                AND decision_type IS NULL
                AND machine_screened_at IS NOT NULL
                AND machine_threshold IS NOT NULL
                AND model_version_id IS NOT NULL)
        )
        """
    )
