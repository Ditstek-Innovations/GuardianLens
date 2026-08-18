"""Tenant marker, users, roles.

Revision ID: 0001
Revises: None

Rules affected: BR-S-02 (structural), ADR-016.

Identity is split across 0001 and 0003 because the dependency is not the
obvious one: detection_rules.created_by references users, while
user_roles.site_id references sites. Creating either subject area whole
would fail — DATABASE.md 13.4.

Note what is NOT created here and never will be: any relation by which an
agent principal could hold a role. `agents` (0003) is a separate table and
`user_roles.user_id` references `users` only. BR-S-02 is a schema property,
not a policy — a fully compromised edge agent cannot verify an event
because the grant relation it would need does not exist.
"""

from __future__ import annotations

from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # gen_random_uuid() is core from PostgreSQL 13; only citext is needed.
    op.execute("CREATE EXTENSION IF NOT EXISTS citext")

    # DATABASE.md 1.4.1 — the anti-misrouting assertion. Exactly one row,
    # read by the Tenant Router immediately after acquiring a connection and
    # before executing anything. In a silo model there is no tenant_id
    # column on the business rows, so nothing in the data can contradict a
    # wrong connection; every constraint would happily accept the writes.
    op.execute(
        """
        CREATE TABLE tenant_identity (
            singleton   BOOLEAN     PRIMARY KEY DEFAULT TRUE,
            tenant_id   UUID        NOT NULL,
            tenant_slug VARCHAR(64) NOT NULL,
            created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT chk_tenant_identity_singleton CHECK (singleton)
        )
        """
    )

    op.execute(
        """
        CREATE TABLE users (
            id                   UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
            email                CITEXT       NOT NULL,
            full_name            VARCHAR(200) NOT NULL,
            password_hash        TEXT,
            external_idp_subject TEXT,
            is_active            BOOLEAN      NOT NULL DEFAULT TRUE,
            created_at           TIMESTAMPTZ  NOT NULL DEFAULT now(),
            updated_at           TIMESTAMPTZ  NOT NULL DEFAULT now(),

            CONSTRAINT uq_users_email UNIQUE (email),
            CONSTRAINT uq_users_idp_subject UNIQUE (external_idp_subject),
            CONSTRAINT chk_users_has_credential CHECK (
                password_hash IS NOT NULL OR external_idp_subject IS NOT NULL
            )
        )
        """
    )

    op.execute(
        """
        CREATE TABLE roles (
            id   UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
            name VARCHAR(50) NOT NULL,
            CONSTRAINT uq_roles_name UNIQUE (name),
            CONSTRAINT chk_roles_name_valid CHECK (
                name IN ('reviewer','safety_manager','site_admin','auditor')
            )
        )
        """
    )

    # Fixed IDs so grants are portable across environments and comparable
    # across tenants — DATABASE.md 14. Seeded per tenant database by the
    # provisioning path, never by hand.
    op.execute(
        """
        INSERT INTO roles (id, name) VALUES
            ('11111111-1111-4111-8111-111111111111', 'reviewer'),
            ('22222222-2222-4222-8222-222222222222', 'safety_manager'),
            ('33333333-3333-4333-8333-333333333333', 'site_admin'),
            ('44444444-4444-4444-8444-444444444444', 'auditor')
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS roles")
    op.execute("DROP TABLE IF EXISTS users")
    op.execute("DROP TABLE IF EXISTS tenant_identity")
