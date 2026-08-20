"""Why Review is empty — last per-camera miss snapshot on the agent row.

Revision ID: 0019
Revises: 0018

The edge already logs why a frame did not become a candidate (wrong class,
stream down, must_be_carried). Reviewers cannot see edge.log. This column
holds the latest health-beat snapshot so GET /events can show the same
reasons on the queue.

DATABASE.md 4.3:

  1. New nullable JSONB on agents. Not a person, frame, or disposition.
  2. No section-6 constraint dropped.
  3. ON DELETE unchanged.
  4. events nullability untouched.
  5. audit_log untouched.
  6. Retention: overwritten on each health beat; no extra store.
  7. RULE_BOOK: display-only telemetry of already-computed miss reasons.

Rules affected: none.
"""

from __future__ import annotations

from alembic import op

revision: str = "0019"
down_revision: str | None = "0018"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE agents
            ADD COLUMN review_block JSONB
        """
    )


def downgrade() -> None:
    op.execute("ALTER TABLE agents DROP COLUMN IF EXISTS review_block")
