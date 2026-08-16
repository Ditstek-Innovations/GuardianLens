"""Per-rule detection class: dynamic YOLO-class-to-rule wiring.

Revision ID: 0012
Revises: 0011

DATABASE.md 4.3 — answer all seven before this revision is approved:

  1. Does it add any column, table, view or index matching DATABASE.md 4.1?
     No. detection_class names which model output class a rule watches for
     (e.g. "person_without_helmet", "backpack") — configuration metadata
     about a rule, not a person, a frame, or anything auto-dispositioned.
     The evaluator already reads Rule.detection_class (guardian_lens_edge
     rules.py); until now the value reaching it was a hardcoded constant,
     never anything a rule actually configured.
  2. Does it drop, weaken or rename any constraint or trigger in section 6?
     No. Purely additive.
  3. Does it change ON DELETE behaviour on any relation in section 3.2?
     No.
  4. Does it alter nullability of reviewer_id, decided_at, decision_type
     or status on events?
     No.
  5. Does it touch audit_log other than adding a nullable column?
     No.
  6. Does it change retention, expiry or deletion semantics?
     No.
  7. Which RULE_BOOK rules does it affect, and how does each remain true?
     None directly — this is a mechanism, not a rule. It stays inside the
     boundary BR-002/BR-006 already draw: detection_class names a
     CONDITION a frame may show (a class the model emits), never an
     identity, and nothing here adds storage for duration, frequency or
     any individual-attributable measure. What a given detection_class is
     USED for is a product-policy question the RULE_BOOK owner answers per
     rule, same as it always was for ppe_helmet — this column does not
     answer it for them.

Rules affected: none directly.

The default keeps every existing ppe_helmet-style rule behaving exactly as
it already did — the evaluator's one wired trigger class, unchanged. New
rules can name any class the tenant's approved model actually emits.
"""

from __future__ import annotations

from alembic import op

revision: str = "0012"
down_revision: str | None = "0011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE detection_rules
            ADD COLUMN detection_class VARCHAR(100)
                NOT NULL DEFAULT 'person_without_helmet'
        """
    )
    op.execute(
        """
        ALTER TABLE detection_rules
            ADD CONSTRAINT chk_detection_rules_detection_class_length
            CHECK (length(detection_class) > 0)
        """
    )


def downgrade() -> None:
    # Production is forward-only (DATABASE.md 13.1). This exists so the
    # revision is reversible in development and testable in CI.
    op.execute(
        "ALTER TABLE detection_rules DROP CONSTRAINT "
        "IF EXISTS chk_detection_rules_detection_class_length"
    )
    op.execute("ALTER TABLE detection_rules DROP COLUMN IF EXISTS detection_class")
