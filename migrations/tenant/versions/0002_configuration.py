"""Sites, cameras, zones, detection rules.

Revision ID: 0002
Revises: 0001

Rules affected: BR-001 (ABSOLUTE), BR-C-02 (PROPOSED), BR-S-03 (PROPOSED),
BR-011 (ADVISORY).

BR-001 — "nothing is monitored by default" — lives in a column default here:
detection_rules.is_active DEFAULT FALSE. A freshly provisioned tenant has no
site, no camera and no rule, so it cannot produce a candidate event. That is
what the clean-instance fitness function (FF-8) asserts.

ON DELETE is RESTRICT throughout, deliberately. DATABASE.md 3.2: CASCADE
from cameras or users to events would let a configuration action silently
delete verified records (BR-007) and their attribution (BR-AU-02).
"""

from __future__ import annotations

from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE sites (
            id             UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
            name           VARCHAR(200) NOT NULL,
            -- IANA name. A reporting period is a shift boundary, and a shift
            -- belongs to a site, not to whoever opens the report (NFR-L-02).
            timezone       VARCHAR(64)  NOT NULL,
            config_version BIGINT       NOT NULL DEFAULT 1,
            created_at     TIMESTAMPTZ  NOT NULL DEFAULT now(),
            updated_at     TIMESTAMPTZ  NOT NULL DEFAULT now()
        )
        """
    )

    op.execute(
        """
        CREATE TABLE cameras (
            id                   UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
            site_id              UUID         NOT NULL
                                 REFERENCES sites(id) ON DELETE RESTRICT,
            name                 VARCHAR(200) NOT NULL,
            location_description TEXT,
            -- AES-256-GCM ciphertext of the RTSP URL including credentials.
            -- There is no plaintext column to leak, the decryption key lives
            -- at the edge, and no API response schema includes this column.
            -- BR-S-03. The control plane stores a credential it cannot read.
            stream_url_encrypted BYTEA        NOT NULL,
            -- Without this, rotating the encryption key means re-entering
            -- every camera credential by hand at every site.
            stream_url_key_id    VARCHAR(64)  NOT NULL,
            stream_profile       VARCHAR(20)  NOT NULL DEFAULT 'secondary',
            sample_rate_fps      NUMERIC(4,2) NOT NULL DEFAULT 2.00,
            status               VARCHAR(20)  NOT NULL DEFAULT 'active',
            created_at           TIMESTAMPTZ  NOT NULL DEFAULT now(),
            updated_at           TIMESTAMPTZ  NOT NULL DEFAULT now(),

            CONSTRAINT chk_cameras_profile_valid CHECK (
                stream_profile IN ('primary','secondary')
            ),
            CONSTRAINT chk_cameras_status_valid CHECK (
                status IN ('active','degraded','disconnected','disabled')
            )
        )
        """
    )

    op.execute(
        """
        CREATE TABLE zones (
            id         UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
            camera_id  UUID         NOT NULL
                       REFERENCES cameras(id) ON DELETE RESTRICT,
            name       VARCHAR(200) NOT NULL,
            -- Vertex array [[x,y],...] in NORMALISED 0-1 space. A pixel-space
            -- polygon would silently move every zone on a resolution or
            -- stream-profile change, producing wrong events that look correct.
            polygon    JSONB        NOT NULL,
            created_at TIMESTAMPTZ  NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ  NOT NULL DEFAULT now()
        )
        """
    )

    op.execute(
        """
        CREATE TABLE detection_rules (
            id                     UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
            zone_id                UUID         NOT NULL
                                   REFERENCES zones(id) ON DELETE RESTRICT,
            rule_type              VARCHAR(50)  NOT NULL,

            -- BR-001, ABSOLUTE. Nothing is monitored by default.
            is_active              BOOLEAN      NOT NULL DEFAULT FALSE,

            -- [OPEN - PRD OQ-4/OQ-5]. Set from pilot data, never from a
            -- published benchmark: published figures are not comparable
            -- across datasets and conditions.
            confidence_threshold   NUMERIC(4,3) NOT NULL,
            debounce_seconds       INTEGER      NOT NULL,
            dwell_seconds          INTEGER,
            -- BR-011 is ADVISORY, so this is nullable; its absence is
            -- flagged at onboarding rather than blocking it.
            written_rule_reference TEXT,
            human_readable         TEXT         NOT NULL,

            created_by             UUID         NOT NULL
                                   REFERENCES users(id) ON DELETE RESTRICT,
            -- BR-C-02: there is no path by which a rule becomes active
            -- without a named user having activated it. Putting the answer
            -- in the row makes attribution a constraint rather than a
            -- reconstruction from audit_log. Gate G2 evidence.
            activated_by           UUID         REFERENCES users(id) ON DELETE RESTRICT,
            activated_at           TIMESTAMPTZ,
            deactivated_at         TIMESTAMPTZ,
            config_version         BIGINT       NOT NULL DEFAULT 1,
            created_at             TIMESTAMPTZ  NOT NULL DEFAULT now(),
            updated_at             TIMESTAMPTZ  NOT NULL DEFAULT now(),

            -- Redundant given NOT NULL plus the foreign key. Retained as a
            -- named artefact because TRD 8.4 and the review checklists refer
            -- to it by name, and a checklist that cannot find its object
            -- reports a false negative.
            CONSTRAINT chk_rule_requires_zone CHECK (zone_id IS NOT NULL),
            CONSTRAINT chk_active_rule_has_activator CHECK (
                is_active = FALSE
                OR (activated_by IS NOT NULL AND activated_at IS NOT NULL)
            )
        )
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS detection_rules")
    op.execute("DROP TABLE IF EXISTS zones")
    op.execute("DROP TABLE IF EXISTS cameras")
    op.execute("DROP TABLE IF EXISTS sites")
