"""Field-level corrections and coverage gaps.

Revision ID: 0007
Revises: 0006

Rules affected: BR-007 (STRONG), BR-W-01 (PROPOSED), FR-005.

event_corrections is INSERT-ONLY and retains original_value — the model's
output. Deleting it would destroy the only ground truth the product ever
collects, and with it the field acceptance rate (AI-01..AI-04) that makes
model regression measurable at all.

One event, MANY corrections — one row per corrected field. TRD 8.2 draws
this as zero-or-one; section 9.6 is field-level, so it is zero-or-many
(AMD-DB-02).

coverage_gaps exists so that a report showing zero events is readable.
Without it, "nothing happened" and "we were not watching" are
indistinguishable, and those are opposite conclusions.
"""

from __future__ import annotations

from alembic import op

revision: str = "0007"
down_revision: str | None = "0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE event_corrections (
            id              UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
            -- CASCADE is correct here and only here: a correction has no
            -- meaning without its event, and the event's own deletion is
            -- retention-governed and audited.
            event_id        UUID        NOT NULL
                            REFERENCES events(id) ON DELETE CASCADE,
            field_name      VARCHAR(64) NOT NULL,
            original_value  TEXT        NOT NULL,
            corrected_value TEXT        NOT NULL,
            corrected_by    UUID        NOT NULL
                            REFERENCES users(id) ON DELETE RESTRICT,
            corrected_at    TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )

    op.execute(
        """
        CREATE TABLE coverage_gaps (
            -- Generated at the edge, where the gap is observed.
            id          UUID        PRIMARY KEY,
            site_id     UUID        NOT NULL
                        REFERENCES sites(id) ON DELETE RESTRICT,
            -- Nullable: an agent_down gap affects the agent, not one camera.
            -- TRD 9.7 makes this NOT NULL while listing agent_down as a
            -- reason, which cannot both hold (AMD-DB-10).
            camera_id   UUID        REFERENCES cameras(id) ON DELETE RESTRICT,
            agent_id    UUID        NOT NULL
                        REFERENCES agents(id) ON DELETE RESTRICT,
            started_at  TIMESTAMPTZ NOT NULL,
            ended_at    TIMESTAMPTZ,
            reason      VARCHAR(50) NOT NULL,
            detail      TEXT,
            -- agent_down is the one gap the edge cannot record; a dead agent
            -- writes nothing. The control plane infers it from missed health
            -- beats, so its resolution is bounded by the beat interval. A gap
            -- inferred coarsely must be distinguishable from one observed
            -- directly, or reports imply a precision the data lacks (R-2).
            recorded_by VARCHAR(20) NOT NULL,

            CONSTRAINT chk_gaps_reason_valid CHECK (
                reason IN ('stream_lost','inference_failure',
                           'agent_down','outbox_full')
            ),
            CONSTRAINT chk_gaps_recorded_by_valid CHECK (
                recorded_by IN ('agent','control_plane')
            ),
            CONSTRAINT chk_gaps_interval_ordered CHECK (
                ended_at IS NULL OR ended_at >= started_at
            )
        )
        """
    )

    # Nothing otherwise prevents two simultaneously open gaps for one agent,
    # camera and reason, which double-counts unavailability in any coverage
    # report (AMD-DB-15). Partial, because it applies only to open gaps.
    op.execute(
        """
        CREATE UNIQUE INDEX uq_coverage_gaps_open
            ON coverage_gaps (
                agent_id,
                COALESCE(camera_id, '00000000-0000-0000-0000-000000000000'::uuid),
                reason
            )
            WHERE ended_at IS NULL
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS coverage_gaps")
    op.execute("DROP TABLE IF EXISTS event_corrections")
