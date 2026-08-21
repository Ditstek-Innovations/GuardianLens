"""SQLAlchemy Core table metadata for the tenant schema.

Query-side metadata ONLY. The schema is owned by migrations/tenant — these
definitions never emit DDL, and any drift between them and the migrations
is a defect in this file. Types are declared to the precision queries need,
not to the precision the DDL carries; constraints and triggers live in the
database where they belong (TRD 8.4).
"""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import BYTEA, INET, JSONB, UUID

metadata = sa.MetaData()

_uuid = UUID(as_uuid=True)
_ts = sa.TIMESTAMP(timezone=True)

#: Marks a primary key the DATABASE generates (gen_random_uuid()); query
#: metadata only — no DDL is ever emitted from these tables.
_DB_GENERATED = sa.FetchedValue()


users = sa.Table(
    "users",
    metadata,
    sa.Column("id", _uuid, primary_key=True, server_default=_DB_GENERATED),
    sa.Column("email", sa.Text),
    sa.Column("full_name", sa.String(200)),
    sa.Column("password_hash", sa.Text),
    sa.Column("is_active", sa.Boolean),
    sa.Column("created_at", _ts),
    sa.Column("updated_at", _ts),
)

roles = sa.Table(
    "roles",
    metadata,
    sa.Column("id", _uuid, primary_key=True, server_default=_DB_GENERATED),
    sa.Column("name", sa.String(50)),
)

user_roles = sa.Table(
    "user_roles",
    metadata,
    sa.Column("user_id", _uuid),
    sa.Column("role_id", _uuid),
    sa.Column("site_id", _uuid),
    sa.Column("granted_by", _uuid),
    sa.Column("granted_at", _ts),
)

agents = sa.Table(
    "agents",
    metadata,
    sa.Column("id", _uuid, primary_key=True, server_default=_DB_GENERATED),
    sa.Column("site_id", _uuid),
    sa.Column("name", sa.String(200)),
    sa.Column("credential_hash", sa.Text),
    sa.Column("last_seen_at", _ts),
    sa.Column("last_health_at", _ts),
    sa.Column("agent_version", sa.String(40)),
    sa.Column("applied_config_version", sa.BigInteger),
    sa.Column("clock_skew_ms", sa.Integer),
    sa.Column("status", sa.String(20)),
    sa.Column("review_block", JSONB),
)

sites = sa.Table(
    "sites",
    metadata,
    sa.Column("id", _uuid, primary_key=True, server_default=_DB_GENERATED),
    sa.Column("name", sa.String(200)),
    sa.Column("timezone", sa.String(64)),
    sa.Column("config_version", sa.BigInteger),
    sa.Column("created_at", _ts),
    sa.Column("updated_at", _ts),
)

cameras = sa.Table(
    "cameras",
    metadata,
    sa.Column("id", _uuid, primary_key=True, server_default=_DB_GENERATED),
    sa.Column("site_id", _uuid),
    sa.Column("name", sa.String(200)),
    sa.Column("location_description", sa.Text),
    sa.Column("stream_url_encrypted", BYTEA),
    sa.Column("stream_url_key_id", sa.String(64)),
    sa.Column("stream_profile", sa.String(20)),
    sa.Column("sample_rate_fps", sa.Numeric(4, 2)),
    sa.Column("status", sa.String(20)),
    sa.Column("created_at", _ts),
    sa.Column("updated_at", _ts),
)

zones = sa.Table(
    "zones",
    metadata,
    sa.Column("id", _uuid, primary_key=True, server_default=_DB_GENERATED),
    sa.Column("camera_id", _uuid),
    sa.Column("name", sa.String(200)),
    sa.Column("polygon", JSONB),
    sa.Column("created_at", _ts),
    sa.Column("updated_at", _ts),
)

detection_rules = sa.Table(
    "detection_rules",
    metadata,
    sa.Column("id", _uuid, primary_key=True, server_default=_DB_GENERATED),
    sa.Column("zone_id", _uuid),
    sa.Column("rule_type", sa.String(50)),
    sa.Column("is_active", sa.Boolean),
    sa.Column("confidence_threshold", sa.Numeric(4, 3)),
    sa.Column("debounce_seconds", sa.Integer),
    sa.Column("dwell_seconds", sa.Integer),
    sa.Column("written_rule_reference", sa.Text),
    sa.Column("human_readable", sa.Text),
    sa.Column("detection_class", sa.String(100)),
    sa.Column("must_be_carried", sa.Boolean),
    sa.Column("created_by", _uuid),
    sa.Column("activated_by", _uuid),
    sa.Column("activated_at", _ts),
    sa.Column("deactivated_at", _ts),
    sa.Column("config_version", sa.BigInteger),
    sa.Column("created_at", _ts),
    sa.Column("updated_at", _ts),
)

model_versions = sa.Table(
    "model_versions",
    metadata,
    sa.Column("id", _uuid, primary_key=True, server_default=_DB_GENERATED),
    sa.Column("version", sa.String(40)),
    sa.Column("artefact_hash", sa.Text),
    sa.Column("training_data_hash", sa.Text),
    sa.Column("classes", JSONB),
    sa.Column("model_card_ref", sa.Text),
    sa.Column("datasheet_ref", sa.Text),
    sa.Column("approved_by", _uuid),
    sa.Column("approved_at", _ts),
    sa.Column("deployed_at", _ts),
    sa.Column("notes", sa.Text),
)

events = sa.Table(
    "events",
    metadata,
    sa.Column("id", _uuid, primary_key=True, server_default=_DB_GENERATED),
    sa.Column("event_id", _uuid),
    sa.Column("site_id", _uuid),
    sa.Column("camera_id", _uuid),
    sa.Column("zone_id", _uuid),
    sa.Column("rule_id", _uuid),
    sa.Column("rule_snapshot", JSONB),
    sa.Column("source", sa.String(20)),
    sa.Column("agent_id", _uuid),
    sa.Column("model_version_id", _uuid),
    sa.Column("confidence", sa.Numeric(4, 3)),
    sa.Column("predicted_class", sa.String(100)),
    sa.Column("predicted_bbox", JSONB),
    sa.Column("occurred_at", _ts),
    sa.Column("received_at", _ts),
    sa.Column("evidence_ref", sa.Text),
    sa.Column("evidence_state", sa.String(20)),
    sa.Column("evidence_blurred", sa.Boolean),
    sa.Column("status", sa.String(20)),
    sa.Column("reviewer_id", _uuid),
    sa.Column("decided_at", _ts),
    sa.Column("decision_type", sa.String(20)),
    sa.Column("rejection_reason", sa.Text),
    sa.Column("version", sa.Integer),
    sa.Column("created_at", _ts),
)

event_corrections = sa.Table(
    "event_corrections",
    metadata,
    sa.Column("id", _uuid, primary_key=True, server_default=_DB_GENERATED),
    sa.Column("event_id", _uuid),
    sa.Column("field_name", sa.String(64)),
    sa.Column("original_value", sa.Text),
    sa.Column("corrected_value", sa.Text),
    sa.Column("corrected_by", _uuid),
    sa.Column("corrected_at", _ts),
)

training_samples = sa.Table(
    "training_samples",
    metadata,
    sa.Column("id", _uuid, primary_key=True, server_default=_DB_GENERATED),
    sa.Column("event_id", _uuid),
    sa.Column("site_id", _uuid),
    sa.Column("decision_type", sa.String(20)),
    sa.Column("class_name", sa.String(100)),
    sa.Column("bbox_norm", JSONB),
    sa.Column("eligible", sa.Boolean),
    sa.Column("reviewed_by", _uuid),
    sa.Column("reviewed_at", _ts),
    sa.Column("created_at", _ts),
)

coverage_gaps = sa.Table(
    "coverage_gaps",
    metadata,
    sa.Column("id", _uuid, primary_key=True),
    sa.Column("site_id", _uuid),
    sa.Column("camera_id", _uuid),
    sa.Column("agent_id", _uuid),
    sa.Column("started_at", _ts),
    sa.Column("ended_at", _ts),
    sa.Column("reason", sa.String(50)),
    sa.Column("detail", sa.Text),
    sa.Column("recorded_by", sa.String(20)),
)

audit_log = sa.Table(
    "audit_log",
    metadata,
    sa.Column("id", sa.BigInteger, primary_key=True),
    sa.Column("actor_user_id", _uuid),
    sa.Column("actor_agent_id", _uuid),
    sa.Column("action", sa.String(64)),
    sa.Column("entity_type", sa.String(50)),
    sa.Column("entity_id", _uuid),
    sa.Column("entity_key", sa.Text),
    sa.Column("before_state", JSONB),
    sa.Column("after_state", JSONB),
    sa.Column("ip_address", INET),
    sa.Column("occurred_at", _ts),
)

# Migration 0010 — refresh-token store, TRD 12.2.
refresh_tokens = sa.Table(
    "refresh_tokens",
    metadata,
    sa.Column("id", _uuid, primary_key=True),
    sa.Column("user_id", _uuid),
    sa.Column("family_id", _uuid),
    sa.Column("token_hash", BYTEA),
    sa.Column("issued_at", _ts),
    sa.Column("expires_at", _ts),
    sa.Column("revoked_at", _ts),
    sa.Column("replaced_by", _uuid),
)

# Migration 0011 — password-reset token store, CS-AU-10 (v1.4).
password_reset_tokens = sa.Table(
    "password_reset_tokens",
    metadata,
    sa.Column("id", _uuid, primary_key=True, server_default=_DB_GENERATED),
    sa.Column("user_id", _uuid),
    sa.Column("token_hash", BYTEA),
    sa.Column("created_at", _ts),
    sa.Column("expires_at", _ts),
    sa.Column("used_at", _ts),
)

camera_discovery_scans = sa.Table(
    "camera_discovery_scans",
    metadata,
    sa.Column("id", _uuid, primary_key=True),
    sa.Column("site_id", _uuid),
    sa.Column("started_at", _ts),
    sa.Column("completed_at", _ts),
    sa.Column("scan_method", sa.String(50)),
    sa.Column("status", sa.String(20)),
    sa.Column("cameras_found", sa.Integer),
)

camera_discovery_candidates = sa.Table(
    "camera_discovery_candidates",
    metadata,
    sa.Column("id", _uuid, primary_key=True),
    sa.Column("scan_id", _uuid),
    sa.Column("site_id", _uuid),
    sa.Column("ip_address", sa.String(50)),
    sa.Column("hostname", sa.String(255)),
    sa.Column("port", sa.Integer),
    sa.Column("rtsp_paths", sa.ARRAY(sa.String)),
    sa.Column("default_rtsp_path", sa.Text),
    sa.Column("resolution", sa.String(50)),
    sa.Column("codec", sa.String(50)),
    sa.Column("model", sa.String(100)),
    sa.Column("manufacturer", sa.String(100)),
    sa.Column("status", sa.String(20)),
    sa.Column("discovered_at", _ts),
    sa.Column("verified_at", _ts),
    sa.Column("imported_at", _ts),
    sa.Column("imported_camera_id", _uuid),
    sa.Column("created_at", _ts),
    sa.Column("updated_at", _ts),
)
