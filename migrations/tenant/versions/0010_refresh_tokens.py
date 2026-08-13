"""Refresh-token store: rotation with reuse detection.

Revision ID: 0010
Revises: 0009

DATABASE.md 4.3 — answer all seven before this revision is approved:

  1. Does it add any column, table, view or index matching DATABASE.md 4.1?
     No. refresh_tokens holds credential-lifecycle state for existing
     users; nothing person-in-frame, per-person, consequence-linked,
     webhook, audio/video, or auto-disposition shaped.
  2. Does it drop, weaken or rename any constraint or trigger in section 6?
     No. Purely additive.
  3. Does it change ON DELETE behaviour on any relation in section 3.2?
     No. The new FK to users is RESTRICT, consistent with 3.2's
     "deactivation, never deletion" posture for users.
  4. Does it alter nullability of reviewer_id, decided_at, decision_type
     or status on events?
     No.
  5. Does it touch audit_log other than adding a nullable column?
     No. Token material must never enter audit_log (DATABASE.md 10.4);
     this table is where token STATE lives instead.
  6. Does it change retention, expiry or deletion semantics?
     No. Rows expire logically via expires_at; physical cleanup of
     long-expired rows is an operational sweep, [V1], and deletes no
     business data.
  7. Which RULE_BOOK rules does it affect, and how does each remain true?
     None directly. It implements TRD 12.2: refresh rotation, reuse
     detection (revoked_at + family_id), and hashes-only storage
     (TRD 12.4 — "refresh-token hashes only; never plaintext").
     chk_refresh_hash_length pins the sha256 form so a plaintext token
     cannot be inserted by accident: plaintext is not 32 bytes.

Rules affected: none. TRD 12.2/12.4 implementation detail.

Why per-tenant rather than in the control database: a refresh token
belongs to a user, users live in tenant databases, and ADR-017 forbids the
control database anything beyond routing. Tenant deprovisioning also takes
the sessions with it, which is exactly right.
"""

from __future__ import annotations

from alembic import op

revision: str = "0010"
down_revision: str | None = "0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE refresh_tokens (
            id          UUID        PRIMARY KEY,
            user_id     UUID        NOT NULL
                        REFERENCES users(id) ON DELETE RESTRICT,
            -- Rotation lineage. Reuse of a revoked member revokes every
            -- open member of the family (TRD 12.2).
            family_id   UUID        NOT NULL,
            -- sha256 of the encoded token. NEVER the token itself.
            token_hash  BYTEA       NOT NULL,
            issued_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
            expires_at  TIMESTAMPTZ NOT NULL,
            revoked_at  TIMESTAMPTZ,
            replaced_by UUID        REFERENCES refresh_tokens(id),

            CONSTRAINT uq_refresh_tokens_hash UNIQUE (token_hash),
            CONSTRAINT chk_refresh_hash_length CHECK (length(token_hash) = 32),
            CONSTRAINT chk_refresh_expiry_ordered CHECK (expires_at > issued_at)
        )
        """
    )

    # The refresh path looks a presented token up by hash (unique index
    # above covers it) and reuse detection walks a family.
    op.execute(
        "CREATE INDEX idx_refresh_tokens_family ON refresh_tokens (family_id)"
    )
    op.execute(
        "CREATE INDEX idx_refresh_tokens_user ON refresh_tokens (user_id)"
    )


def downgrade() -> None:
    # Production is forward-only (DATABASE.md 13.1). This exists so the
    # revision is reversible in development and testable in CI.
    op.execute("DROP TABLE IF EXISTS refresh_tokens")
