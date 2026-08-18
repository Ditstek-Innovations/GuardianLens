"""Remove the per-rule review flag — superseded by the queue-level design.

Revision ID: 0014
Revises: 0013

The 0013 flag marked candidates rule-by-rule. The product direction the
owner is being asked to ratify (Docs/PROPOSAL_AI_ASSISTED_REVIEW.md) puts
the reviewer-availability mode on the QUEUE, not on individual rules, so
the rule-level flag is withdrawn before it accumulates users. Review
obligations are untouched: with or without any flag, every candidate still
requires a Reviewer decision (BR-004/BR-005).

DATABASE.md 4.3 — the seven questions:

  1. Adds nothing (4.1): pure column removal.
  2. Drops/weakens a section-6 constraint or trigger? No — flag_for_review
     carried no CHECK and no registry entry; nothing FF-11 attests changes.
  3. ON DELETE behaviour: unchanged.
  4. events nullability: untouched.
  5. audit_log: untouched (the field also leaves the audit allowlist in the
     same change, so no writer can offer it).
  6. Retention/expiry: unchanged.
  7. RULE_BOOK rules affected: none — the column never fed a decision path,
     which is precisely why it can be removed without one.

Rules affected: none.
"""

from __future__ import annotations

from alembic import op

revision: str = "0014"
down_revision: str | None = "0013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE detection_rules DROP COLUMN IF EXISTS flag_for_review")


def downgrade() -> None:
    # Production is forward-only (DATABASE.md 13.1); reversible for dev/CI.
    op.execute(
        """
        ALTER TABLE detection_rules
            ADD COLUMN flag_for_review BOOLEAN NOT NULL DEFAULT TRUE
        """
    )
