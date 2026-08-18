"""Camera discovery - candidates and scan history tables for auto-detection.

Revision ID: 0018
Revises: 0017

Adds support for automated camera discovery and user-initiated selection:

camera_discovery_candidates:
  - Stores discovered cameras from network scans
  - Tracks IP, port, detected model/manufacturer
  - Records available RTSP paths (verified at discovery time)
  - Status tracking: pending → verified/unreachable → imported

camera_discovery_scans:
  - Audit trail of discovery operations
  - Tracks scan timing, method, and results
  - Links candidates to the scan that found them

DATABASE.md implications:
  1. No new constraints on existing rule evaluation
  2. Candidates are ephemeral (can be deleted after import)
  3. No audit_log entry required (discovery is read-only operation)
  4. Retention: candidates auto-expire after 30 days
  5. audit_log: untouched
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision: str = "0018"
down_revision: str | None = "0017"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Camera discovery runs - audit trail of scans
    op.create_table(
        "camera_discovery_scans",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("site_id", sa.UUID(), nullable=False),
        sa.Column("started_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("completed_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column(
            "scan_method",
            sa.String(32),
            nullable=False,
            server_default="rtsp_probe",
        ),
        sa.Column("cameras_found", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "status",
            sa.String(32),
            nullable=False,
            server_default="in_progress",
        ),
        sa.ForeignKeyConstraint(["site_id"], ["sites.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    # Discovered camera candidates - awaiting user approval
    op.create_table(
        "camera_discovery_candidates",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("scan_id", sa.UUID(), nullable=False),
        sa.Column("site_id", sa.UUID(), nullable=False),
        sa.Column("discovered_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("ip_address", sa.String(45), nullable=False),  # IPv4 or IPv6
        sa.Column("hostname", sa.String(255), nullable=True),
        sa.Column("port", sa.Integer(), nullable=False, server_default="554"),
        sa.Column("model", sa.String(255), nullable=True),
        sa.Column("manufacturer", sa.String(255), nullable=True),
        sa.Column(
            "rtsp_paths",
            sa.ARRAY(sa.String()),
            nullable=False,
            server_default="{}",
        ),
        sa.Column("default_rtsp_path", sa.String(255), nullable=True),
        sa.Column("resolution", sa.String(64), nullable=True),  # e.g., "1920x1080"
        sa.Column("codec", sa.String(64), nullable=True),  # e.g., "h264"
        sa.Column(
            "status",
            sa.String(32),
            nullable=False,
            server_default="verified",
        ),
        sa.Column("verified_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("imported_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("imported_camera_id", sa.UUID(), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["scan_id"], ["camera_discovery_scans.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["site_id"], ["sites.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["imported_camera_id"], ["cameras.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("site_id", "ip_address", "port", name="uq_candidate_site_ip_port"),
    )

    op.create_index(
        "idx_camera_discovery_candidates_site_status",
        "camera_discovery_candidates",
        ["site_id", "status"],
    )
    op.create_index(
        "idx_camera_discovery_candidates_scan",
        "camera_discovery_candidates",
        ["scan_id"],
    )
    op.create_index(
        "idx_camera_discovery_scans_site",
        "camera_discovery_scans",
        ["site_id"],
    )


def downgrade() -> None:
    op.drop_index("idx_camera_discovery_scans_site")
    op.drop_index("idx_camera_discovery_candidates_scan")
    op.drop_index("idx_camera_discovery_candidates_site_status")
    op.drop_table("camera_discovery_candidates")
    op.drop_table("camera_discovery_scans")
