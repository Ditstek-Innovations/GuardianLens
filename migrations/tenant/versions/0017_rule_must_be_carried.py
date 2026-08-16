"""Per-rule person-context requirement — the held-vs-lying discriminator.

Revision ID: 0017
Revises: 0016

A rule like "Mobile phone in use" should mean IN USE: with this flag the
condition only fires when its detection box sits inside a detected
person's box in the same frame — a phone lying alone on furniture does
not. Pure per-frame geometry, evaluated deterministically at the edge
(BR-D-03); no identity, no tracking, no cross-frame association of any
kind is introduced (BR-002/BR-006 untouched).

DATABASE.md 4.3 — the seven questions:

  1. Adds a rule-configuration boolean. Nothing person-in-frame is stored;
     the geometry is evaluated and discarded at the edge, and a failed
     check is COUNTED (BR-D-02 context_unmet counter), never silent.
  2. Drops/weakens a section-6 constraint? No — purely additive.
  3. ON DELETE behaviour: unchanged.
  4. events nullability: untouched.
  5. audit_log: untouched (the field joins the rule audit allowlist).
  6. Retention/expiry: unchanged.
  7. RULE_BOOK rules affected: none — strengthens BR-D-03's determinism
     story (the check is arithmetic on already-produced detections) and
     narrows what fires, never widens it.

Rules affected: none directly.
"""

from __future__ import annotations

from alembic import op

revision: str = "0017"
down_revision: str | None = "0016"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE detection_rules
            ADD COLUMN must_be_carried BOOLEAN NOT NULL DEFAULT FALSE
        """
    )


def downgrade() -> None:
    # Production is forward-only (DATABASE.md 13.1); reversible for dev/CI.
    op.execute(
        "ALTER TABLE detection_rules DROP COLUMN IF EXISTS must_be_carried"
    )
