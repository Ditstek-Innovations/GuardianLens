"""Tenant registry, routing, login directory, lifecycle audit.

Revision ID: c0001
Revises: None

Rules affected: none directly. ADR-016, ADR-017.

This schema holds ROUTING, LIFECYCLE AND OPERATIONAL STATE ONLY. It is
reachable from every request, which makes it the natural place to cache
"just a little" tenant data — a display name, a site count, a last-login.
Each such addition is individually harmless and collectively rebuilds a
shared, cross-tenant copy of exactly the data ADR-016 separated.

Compromise of this database must yield the MAP, not the TERRITORY: per-tenant
credentials live in the secret store and only a reference is held here, so
the registry alone grants no access (threat T-20).

A "tenant health dashboard" is the boundary case to police. Counts of
OPERATIONAL state — schema version, attestation, last migration — are
permitted. Counts of BUSINESS state — events, decisions, reviewers — are not.
"""

from __future__ import annotations

from alembic import op

revision: str = "c0001"
down_revision: str | None = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE tenants (
            id             UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
            slug           VARCHAR(64)  NOT NULL,
            display_name   VARCHAR(200) NOT NULL,
            status         VARCHAR(20)  NOT NULL DEFAULT 'provisioning',
            provisioned_at TIMESTAMPTZ,
            suspended_at   TIMESTAMPTZ,
            -- Tombstone. Deleting the row alongside the database would erase
            -- the record that the tenant ever existed, including the audited
            -- fact of the deletion. The data goes; the fact of its deletion
            -- does not. BR-009 applied one level above the schema.
            deleted_at     TIMESTAMPTZ,
            created_at     TIMESTAMPTZ  NOT NULL DEFAULT now(),
            updated_at     TIMESTAMPTZ  NOT NULL DEFAULT now(),

            CONSTRAINT uq_tenants_slug UNIQUE (slug),
            CONSTRAINT chk_tenants_slug_format CHECK (slug ~ '^[a-z0-9][a-z0-9_-]*$'),
            CONSTRAINT chk_tenants_status_valid CHECK (
                status IN ('provisioning','active','suspended',
                           'drifted','deprovisioned')
            ),
            CONSTRAINT chk_tenant_active_is_provisioned CHECK (
                status <> 'active' OR provisioned_at IS NOT NULL
            )
        )
        """
    )

    op.execute(
        """
        CREATE TABLE tenant_databases (
            tenant_id       UUID         PRIMARY KEY
                            REFERENCES tenants(id) ON DELETE RESTRICT,
            host            VARCHAR(255) NOT NULL,
            port            INTEGER      NOT NULL DEFAULT 5432,
            database_name   VARCHAR(63)  NOT NULL,
            -- A REFERENCE into the secret store. Never the credential.
            credential_ref  VARCHAR(255) NOT NULL,
            evidence_prefix VARCHAR(255) NOT NULL,

            CONSTRAINT uq_tenant_databases_target UNIQUE (host, port, database_name)
        )
        """
    )

    op.execute(
        """
        CREATE TABLE tenant_schema_versions (
            tenant_id        UUID        PRIMARY KEY
                             REFERENCES tenants(id) ON DELETE RESTRICT,
            current_revision VARCHAR(64) NOT NULL,
            target_revision  VARCHAR(64) NOT NULL,
            last_attempt_at  TIMESTAMPTZ,
            last_outcome     VARCHAR(20),
            last_error       TEXT,
            -- FF-11. A tenant reaches 'active' only by passing attestation;
            -- a tenant failing it is refused binding, not merely alerted.
            attested_at      TIMESTAMPTZ,
            attestation_ok   BOOLEAN,

            CONSTRAINT chk_schema_outcome_valid CHECK (
                last_outcome IS NULL
                OR last_outcome IN ('success','failed','skipped')
            )
        )
        """
    )

    # Login routing only. A login by email must resolve to a tenant before
    # any tenant database is opened — this is the one place where a
    # cross-tenant surface necessarily exists (DATABASE.md 1.5).
    #
    # The address itself is NEVER stored. Hashing protects the directory at
    # rest; it does not stop probing, and the residual enumeration risk is
    # real and irreducible while login is by email alone (threat T-19,
    # risk R-10). The complete fix is tenant-scoped login.
    op.execute(
        """
        CREATE TABLE user_directory (
            email_hash BYTEA       PRIMARY KEY,
            tenant_id  UUID        NOT NULL
                       REFERENCES tenants(id) ON DELETE RESTRICT,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),

            CONSTRAINT chk_directory_hash_length CHECK (length(email_hash) = 32)
        )
        """
    )
    op.execute("CREATE INDEX idx_user_directory_tenant ON user_directory (tenant_id)")

    op.execute(
        """
        CREATE TABLE control_audit_log (
            id           BIGSERIAL    PRIMARY KEY,
            actor        VARCHAR(200) NOT NULL,
            action       VARCHAR(64)  NOT NULL,
            tenant_id    UUID         REFERENCES tenants(id) ON DELETE RESTRICT,
            before_state JSONB,
            after_state  JSONB,
            occurred_at  TIMESTAMPTZ  NOT NULL DEFAULT now()
        )
        """
    )

    # Same append-only posture as the tenant audit_log, for the same reason:
    # tenant lifecycle is exactly the kind of scope change BR-010 requires to
    # be recorded and attributable.
    op.execute(
        """
        CREATE OR REPLACE FUNCTION fn_control_audit_append_only()
        RETURNS TRIGGER AS $$
        BEGIN
            RAISE EXCEPTION
                'control_audit_log is append-only; % rejected', TG_OP
                USING ERRCODE = 'restrict_violation';
        END;
        $$ LANGUAGE plpgsql
        """
    )
    op.execute(
        """
        CREATE TRIGGER trg_control_audit_append_only
            BEFORE UPDATE OR DELETE ON control_audit_log
            FOR EACH ROW EXECUTE FUNCTION fn_control_audit_append_only()
        """
    )
    op.execute(
        """
        CREATE TRIGGER trg_control_audit_no_truncate
            BEFORE TRUNCATE ON control_audit_log
            FOR EACH STATEMENT EXECUTE FUNCTION fn_control_audit_append_only()
        """
    )


def downgrade() -> None:
    op.execute(
        "DROP TRIGGER IF EXISTS trg_control_audit_no_truncate ON control_audit_log"
    )
    op.execute(
        "DROP TRIGGER IF EXISTS trg_control_audit_append_only ON control_audit_log"
    )
    op.execute("DROP FUNCTION IF EXISTS fn_control_audit_append_only()")
    op.execute("DROP TABLE IF EXISTS control_audit_log")
    op.execute("DROP TABLE IF EXISTS user_directory")
    op.execute("DROP TABLE IF EXISTS tenant_schema_versions")
    op.execute("DROP TABLE IF EXISTS tenant_databases")
    op.execute("DROP TABLE IF EXISTS tenants")
