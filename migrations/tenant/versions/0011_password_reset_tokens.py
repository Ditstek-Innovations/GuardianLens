"""Password-reset token store: single-use, short-lived, hashes only.

Revision ID: 0011
Revises: 0010

DATABASE.md 4.3 — answer all seven before this revision is approved:

  1. Does it add any column, table, view or index matching DATABASE.md 4.1?
     No. password_reset_tokens holds credential-lifecycle state for
     existing users; nothing person-in-frame, per-person, consequence-
     linked, webhook, audio/video, or auto-disposition shaped.
  2. Does it drop, weaken or rename any constraint or trigger in section 6?
     No. Purely additive.
  3. Does it change ON DELETE behaviour on any relation in section 3.2?
     No — no existing relation changes. The NEW FK to users is CASCADE,
     deliberately unlike refresh_tokens' RESTRICT: a reset token is
     meaningless without its user and holds nothing auditable — it is a
     pending capability, not a record of anything that happened — so it
     must never be the row that blocks a user's removal.
  4. Does it alter nullability of reviewer_id, decided_at, decision_type
     or status on events?
     No.
  5. Does it touch audit_log other than adding a nullable column?
     No. Token material must never enter audit_log (DATABASE.md 10.4);
     this table is where reset-token STATE lives instead.
  6. Does it change retention, expiry or deletion semantics?
     No. Rows expire logically via expires_at (the service sets a
     30-minute TTL) and die with their user via the CASCADE; physical
     cleanup of long-expired rows is an operational sweep, [V1], and
     deletes no business data.
  7. Which RULE_BOOK rules does it affect, and how does each remain true?
     None directly. It implements the CS-AU-10 v1.4 owner decision
     (self-service password reset) under the TRD 12.4 discipline:
     hashes only, never plaintext. chk_reset_hash_length pins the
     sha256 form so a plaintext token cannot be inserted by accident:
     plaintext is not 32 bytes. used_at makes single-use a fact the
     row records rather than a behaviour the service promises.

Rules affected: none. CS-AU-10 (v1.4) / TRD 12.4 implementation detail.

Why per-tenant rather than in the control database: a reset token belongs
to a user, users live in tenant databases, and ADR-017 forbids the control
database anything beyond routing. Tenant deprovisioning also takes the
pending resets with it, which is exactly right.
"""

from __future__ import annotations

from alembic import op

revision: str = "0011"
down_revision: str | None = "0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE password_reset_tokens (
            id         UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id    UUID        NOT NULL
                       REFERENCES users(id) ON DELETE CASCADE,
            -- sha256 of the token. NEVER the token itself.
            token_hash BYTEA       NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            expires_at TIMESTAMPTZ NOT NULL,
            -- Single use. A fresh request also stamps this on every prior
            -- live token, so at most one token per user can ever redeem.
            used_at    TIMESTAMPTZ,

            CONSTRAINT uq_password_reset_tokens_hash UNIQUE (token_hash),
            CONSTRAINT chk_reset_hash_length CHECK (length(token_hash) = 32),
            CONSTRAINT chk_reset_expiry_ordered CHECK (expires_at > created_at)
        )
        """
    )

    # The reset path looks a presented token up by hash (unique index above
    # covers it); superseding walks a user's live tokens.
    op.execute(
        "CREATE INDEX idx_password_reset_tokens_user"
        " ON password_reset_tokens (user_id)"
    )


def downgrade() -> None:
    # Production is forward-only (DATABASE.md 13.1). This exists so the
    # revision is reversible in development and testable in CI.
    op.execute("DROP TABLE IF EXISTS password_reset_tokens")
