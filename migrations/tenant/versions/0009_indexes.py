"""Indexes serving the named queries in DATABASE.md 7.1.

Revision ID: 0009
Revises: 0008

Rules affected: BR-R-01 (ABSOLUTE, via the partial reporting index).

An index without a query is speculative cost; a query without an index is a
future incident. Every index below names the query it serves.

CREATE INDEX CONCURRENTLY is the production form (DATABASE.md 13.2) but
cannot run inside a transaction, and Alembic wraps each revision in one.
On an empty baseline the lock is instantaneous, so plain CREATE INDEX is
correct here. Any index added to a populated table is a separate, concurrent
revision.
"""

from __future__ import annotations

from alembic import op

revision: str = "0009"
down_revision: str | None = "0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Q-1, the review queue: the hottest read path and the one a reviewer
    # feels directly. PARTIAL, so its size tracks the undisposed backlog
    # rather than total history — queue performance stays flat as a site
    # accumulates years of verified records. site_id leads so the ADR-012
    # scope filter is served by the same index.
    op.execute(
        """
        CREATE INDEX idx_events_queue
            ON events (site_id, occurred_at DESC)
            WHERE status = 'unverified'
        """
    )

    # Q-3, reporting. Also partial: every report query filters
    # status IN ('accepted','corrected') at the repository layer (BR-R-01),
    # so a full index would carry rows no report can ever read.
    op.execute(
        """
        CREATE INDEX idx_events_site_occurred
            ON events (site_id, occurred_at DESC)
            WHERE status IN ('accepted','corrected')
        """
    )

    op.execute(
        """
        CREATE INDEX idx_events_zone_rule
            ON events (zone_id, rule_id, occurred_at DESC)
        """
    )

    op.execute(
        """
        CREATE INDEX idx_events_reviewer
            ON events (reviewer_id, decided_at DESC)
            WHERE reviewer_id IS NOT NULL
        """
    )

    # Q-9, the retention sweep. received_at, not occurred_at: retention must
    # not be shortened or extended by a wrong edge clock (ADR-007).
    op.execute("CREATE INDEX idx_events_received ON events (received_at)")

    # Q-7. Audit retrieval must never be the slow path.
    op.execute(
        """
        CREATE INDEX idx_audit_entity_time
            ON audit_log (entity_type, entity_id, occurred_at DESC)
        """
    )

    # Q-8, coverage reporting.
    op.execute(
        "CREATE INDEX idx_gaps_site_period ON coverage_gaps (site_id, started_at DESC)"
    )
    op.execute(
        "CREATE INDEX idx_gaps_open ON coverage_gaps (agent_id) WHERE ended_at IS NULL"
    )

    # Supporting.
    op.execute("CREATE INDEX idx_cameras_site ON cameras (site_id)")
    op.execute("CREATE INDEX idx_zones_camera ON zones (camera_id)")
    op.execute(
        "CREATE INDEX idx_rules_zone_active ON detection_rules (zone_id) WHERE is_active"
    )
    op.execute("CREATE INDEX idx_corrections_event ON event_corrections (event_id)")
    op.execute("CREATE INDEX idx_user_roles_site ON user_roles (site_id, user_id)")


def downgrade() -> None:
    for name in (
        "idx_user_roles_site",
        "idx_corrections_event",
        "idx_rules_zone_active",
        "idx_zones_camera",
        "idx_cameras_site",
        "idx_gaps_open",
        "idx_gaps_site_period",
        "idx_audit_entity_time",
        "idx_events_received",
        "idx_events_reviewer",
        "idx_events_zone_rule",
        "idx_events_site_occurred",
        "idx_events_queue",
    ):
        op.execute(f"DROP INDEX IF EXISTS {name}")
