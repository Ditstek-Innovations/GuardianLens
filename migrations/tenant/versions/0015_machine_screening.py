"""Machine-disposition tier — BR-004 (1.1) Machine-Screened Outcomes.

Revision ID: 0015
Revises: 0014

HISTORICAL REVISION — the tier this created was withdrawn the same day by
migration 0016 (AMD-RB-05 withdrawn before ratification, RULE_BOOK 1.2).
This file must exist as long as any database's migration history includes
it: deleting a revision script does not delete the fact that it ran.

Implemented the AMD-RB-05 amendment applied to RULE_BOOK.md 1.1. Migration
0005's own comment demanded that a status like this arrive as "an
unmistakable rewrite of a named constraint rather than a one-line ALTER
TYPE". This was that rewrite. See 0016 for the removal and the seven-
question answers of both directions.

Rules affected at the time: BR-004 (1.1), BR-V-03 (1.1) — both since
restored to their 1.0 text.
"""

from __future__ import annotations

from alembic import op

revision: str = "0015"
down_revision: str | None = "0014"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # The site-level mode switch — off by default (BR-001 discipline), the
    # threshold stated per site, bounded like every confidence.
    op.execute(
        """
        ALTER TABLE sites
            ADD COLUMN auto_review_enabled BOOLEAN NOT NULL DEFAULT FALSE,
            ADD COLUMN auto_review_threshold NUMERIC(4,3) NOT NULL DEFAULT 0.800,
            ADD CONSTRAINT chk_sites_auto_review_threshold
                CHECK (auto_review_threshold > 0 AND auto_review_threshold <= 1)
        """
    )
    # Machine-screening provenance on the event — BR-004 (1.1)(c).
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
            -- BR-004 (1.1): a Machine-Screened Outcome NEVER carries a
            -- reviewer (it is not a decision) and ALWAYS carries its
            -- provenance.
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


def downgrade() -> None:
    # Production is forward-only (DATABASE.md 13.1); reversible for dev/CI.
    # Screened rows must be re-opened before the constraint can narrow.
    op.execute(
        """
        UPDATE events SET status = 'unverified',
                          machine_screened_at = NULL,
                          machine_threshold = NULL
         WHERE status = 'machine_screened'
        """
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
