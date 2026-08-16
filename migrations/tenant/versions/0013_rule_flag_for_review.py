"""Per-rule review flag: a priority marker, never a bypass of BR-004.

Revision ID: 0013
Revises: 0012

DATABASE.md 4.3 — answer all seven before this revision is approved:

  1. Does it add any column, table, view or index matching DATABASE.md 4.1?
     No. flag_for_review is display/triage metadata about a RULE — which
     candidates a reviewer should treat as higher priority in the queue.
     It is not a person, a frame, a consequence link, a webhook, audio/
     video, or (this is the load-bearing point) an auto-disposition path:
     no code path this column feeds ever writes status, reviewer_id or
     decided_at. It changes ordering/labelling only.
  2. Does it drop, weaken or rename any constraint or trigger in section 6?
     No. Purely additive, and in particular touches nothing in the D2
     decision ladder (ARCHITECTURE.md 5.5) or chk_decided_requires_reviewer.
  3. Does it change ON DELETE behaviour on any relation in section 3.2?
     No.
  4. Does it alter nullability of reviewer_id, decided_at, decision_type
     or status on events?
     No — and it does not touch the events table at all. A candidate's
     flagged-ness is read from its frozen rule_snapshot (which already
     carries flag_for_review once served, same mechanism as 0012's
     detection_class), not a new column on events.
  5. Does it touch audit_log other than adding a nullable column?
     No.
  6. Does it change retention, expiry or deletion semantics?
     No.
  7. Which RULE_BOOK rules does it affect, and how does each remain true?
     BR-004, BR-005, BR-V-03 remain exactly as enforced: every Candidate
     Event, flagged or not, still requires an authorised Reviewer's
     accept/reject/correct before it is a Verified Record —
     chk_decided_requires_reviewer is untouched, and no route this
     revision touches can write a decision. flag_for_review can reorder
     or annotate the queue (which BR-V-03 permits confidence to do
     already); it cannot substitute for a Reviewer, and nothing in this
     migration, the schema, or the service layer gives it that power.

Rules affected: none directly — reinforces BR-004/BR-005/BR-V-03 by
construction (the column has no path to a decision).

Defaults to TRUE: every rule's candidates are flagged for review right now,
matching current practice. A rule can be created or patched with
flag_for_review=false later, for a rule the site trusts enough not to want
it visually called out — review is still mandatory either way.
"""

from __future__ import annotations

from alembic import op

revision: str = "0013"
down_revision: str | None = "0012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE detection_rules
            ADD COLUMN flag_for_review BOOLEAN NOT NULL DEFAULT TRUE
        """
    )


def downgrade() -> None:
    # Production is forward-only (DATABASE.md 13.1). This exists so the
    # revision is reversible in development and testable in CI.
    op.execute("ALTER TABLE detection_rules DROP COLUMN IF EXISTS flag_for_review")
