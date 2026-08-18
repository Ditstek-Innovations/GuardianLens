"""${message}

Revision ID: ${up_revision}
Revises: ${down_revision | comma,n}
Create Date: ${create_date}

DATABASE.md 4.3 — answer all seven before this revision is approved:

  1. Does it add any column, table, view or index matching DATABASE.md 4.1?
  2. Does it drop, weaken or rename any constraint or trigger in section 6?
  3. Does it change ON DELETE behaviour on any relation in section 3.2?
  4. Does it alter nullability of reviewer_id, decided_at, decision_type
     or status on events?
  5. Does it touch audit_log other than adding a nullable column?
  6. Does it change retention, expiry or deletion semantics?
  7. Which RULE_BOOK rules does it affect, and how does each remain true?

Any yes to 1-6 makes this T3 (GOVERNANCE.md 8.2): SARB review, then the
Decide holder. Question 7 is mandatory on every T3 RFC regardless.

Rules affected: <state them, or "none">
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
${imports if imports else ""}

revision: str = ${repr(up_revision)}
down_revision: str | None = ${repr(down_revision)}
branch_labels = ${repr(branch_labels)}
depends_on = ${repr(depends_on)}


def upgrade() -> None:
    ${upgrades if upgrades else "pass"}


def downgrade() -> None:
    # Production is forward-only (DATABASE.md 13.1). This exists so the
    # revision is reversible in development and testable in CI.
    ${downgrades if downgrades else "pass"}
