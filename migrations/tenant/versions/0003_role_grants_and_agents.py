"""Role grants and agent principals.

Revision ID: 0003
Revises: 0002

Rules affected: BR-S-02 (PROPOSED, structural), BR-010.

This is the revision that makes BR-S-02 true, and it does so by what it does
NOT create. `user_roles.user_id` references `users`. There is no
`agent_roles` table and no nullable actor column through which an agent
principal could be granted a role. A fully compromised edge agent cannot
verify an event because the grant relation it would need does not exist.

Removing that guarantee would require dropping and rebuilding the
authorisation model, not changing a check. That is the strongest form of
enforcement available — see DATABASE.md 5.8 and bypass case DB-15.

user_roles.site_id is NOT NULL. A nullable column in a composite primary key
is silently impossible to insert in PostgreSQL, so a "global role" expressed
as site_id IS NULL would appear configured and would not exist. A cross-site
principal is expressed as multiple rows — AMD-DB-13.
"""

from __future__ import annotations

from alembic import op

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE user_roles (
            user_id    UUID        NOT NULL
                       REFERENCES users(id) ON DELETE RESTRICT,
            role_id    UUID        NOT NULL
                       REFERENCES roles(id) ON DELETE RESTRICT,
            site_id    UUID        NOT NULL
                       REFERENCES sites(id) ON DELETE RESTRICT,
            granted_by UUID        REFERENCES users(id) ON DELETE RESTRICT,
            granted_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            PRIMARY KEY (user_id, role_id, site_id)
        )
        """
    )

    op.execute(
        """
        CREATE TABLE agents (
            id                     UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
            site_id                UUID         NOT NULL
                                   REFERENCES sites(id) ON DELETE RESTRICT,
            name                   VARCHAR(200) NOT NULL,
            -- Argon2id. An agent principal holds no review permission, ever.
            credential_hash        TEXT         NOT NULL,
            last_seen_at           TIMESTAMPTZ,
            -- Drives agent_down gap inference. A dead agent writes nothing,
            -- so the control plane infers the gap from missed health beats,
            -- and the beat interval bounds that gap's resolution.
            last_health_at         TIMESTAMPTZ,
            agent_version          VARCHAR(40),
            -- ADR-008: the version the agent is ACTUALLY running. The
            -- control plane's view of a site's monitored scope is an
            -- intention; this is the fact. A mismatch persisting beyond one
            -- sync interval is alertable, because otherwise BR-001 is
            -- asserted rather than observed.
            applied_config_version BIGINT,
            -- ADR-007: measured on each health beat. Timestamps are never
            -- silently corrected; a corrected timestamp is a fabricated
            -- observation.
            clock_skew_ms          INTEGER,
            status                 VARCHAR(20)  NOT NULL DEFAULT 'offline',

            CONSTRAINT chk_agents_status_valid CHECK (
                status IN ('active','degraded','offline')
            )
        )
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS agents")
    op.execute("DROP TABLE IF EXISTS user_roles")
