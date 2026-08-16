"""ConfigRepository — sites, cameras, zones, detection rules, coverage gaps.

Persistence only; the attribution and audit rules around these mutations
live in ConfigurationService and its guards. Note that no read method here
ever selects stream_url_encrypted except the agent-config document builder,
which is the one designed consumer (credentials are delivered sealed and
decrypted only at the edge — ARCHITECTURE.md 8.10).
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from typing import Any
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.orm import Session

from guardian_lens.repositories.tables import (
    agents,
    cameras,
    coverage_gaps,
    detection_rules,
    model_versions,
    sites,
    zones,
)

__all__ = ["ConfigRepository"]

#: Agent columns safe for any response or audit path. credential_hash is
#: deliberately absent — the secret is returned exactly once at registration
#: and its hash never leaves the repository (TRD 12.4 discipline).
_AGENT_PUBLIC = [
    agents.c.id,
    agents.c.site_id,
    agents.c.name,
    agents.c.status,
    agents.c.last_seen_at,
    agents.c.last_health_at,
    agents.c.agent_version,
    agents.c.applied_config_version,
    agents.c.clock_skew_ms,
]

#: The stored `cameras.status` column only ever holds what an admin set
#: (active on creation, or disabled/active via the enable/disable toggle —
#: ConfigurationService.update_camera). It carries no signal from the edge.
#: The live signal already exists — the same coverage-gap row the "prove
#: honesty" test in CAMERA_INTEGRATION.md §5 reads — so status is derived,
#: never a second value that could drift out of sync with it. An admin
#: disable always wins over stream state; otherwise an OPEN stream_lost gap
#: (ended_at IS NULL) means disconnected. 'degraded' has no signal path yet
#: (MOD-1's decode-failure streak is edge-log-only, no persisted gap).
_CAMERA_LIVE_STATUS = sa.case(
    (cameras.c.status == "disabled", cameras.c.status),
    (
        sa.exists(
            sa.select(1).where(
                coverage_gaps.c.camera_id == cameras.c.id,
                coverage_gaps.c.reason == "stream_lost",
                coverage_gaps.c.ended_at.is_(None),
            )
        ),
        sa.literal("disconnected"),
    ),
    else_=cameras.c.status,
).label("status")

#: Camera columns safe for any response or audit path. stream_url_encrypted
#: is deliberately absent — it never leaves the repository except toward the
#: agent config document.
_CAMERA_PUBLIC = [
    cameras.c.id,
    cameras.c.site_id,
    cameras.c.name,
    cameras.c.location_description,
    cameras.c.stream_profile,
    cameras.c.sample_rate_fps,
    _CAMERA_LIVE_STATUS,
    cameras.c.created_at,
    cameras.c.updated_at,
]


class ConfigRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    # -- sites ---------------------------------------------------------------

    def insert_site(self, values: dict[str, Any]) -> sa.Row:
        return self._session.execute(
            sa.insert(sites).values(**values).returning(sites)
        ).one()

    def list_sites(self, site_ids: Sequence[UUID]) -> Sequence[sa.Row]:
        return self._session.execute(
            sa.select(sites).where(sites.c.id.in_(list(site_ids)))
            .order_by(sites.c.name)
        ).all()

    def get_site(self, site_id: UUID) -> sa.Row | None:
        return self._session.execute(
            sa.select(sites).where(sites.c.id == site_id)
        ).one_or_none()

    def bump_config_version(self, site_id: UUID) -> int:
        """Increment the site's config version. Called inside every
        configuration transaction so agent config pulls (IF-X1) observe a
        change exactly when one was committed."""
        return self._session.execute(
            sa.update(sites)
            .where(sites.c.id == site_id)
            .values(config_version=sites.c.config_version + 1)
            .returning(sites.c.config_version)
        ).scalar_one()

    # -- cameras -------------------------------------------------------------

    def insert_camera(self, values: dict[str, Any]) -> sa.Row:
        pk = self._session.execute(
            sa.insert(cameras).values(**values).returning(cameras.c.id)
        ).scalar_one()
        return self.get_camera(pk)  # type: ignore[return-value]

    def get_camera(self, camera_id: UUID) -> sa.Row | None:
        return self._session.execute(
            sa.select(*_CAMERA_PUBLIC).where(cameras.c.id == camera_id)
        ).one_or_none()

    def list_cameras(self, site_ids: Sequence[UUID]) -> Sequence[sa.Row]:
        return self._session.execute(
            sa.select(*_CAMERA_PUBLIC)
            .where(cameras.c.site_id.in_(list(site_ids)))
            .order_by(cameras.c.name)
        ).all()

    def update_camera(self, camera_id: UUID, values: dict[str, Any]) -> sa.Row | None:
        result = self._session.execute(
            sa.update(cameras).where(cameras.c.id == camera_id).values(**values)
        )
        if result.rowcount != 1:
            return None
        return self.get_camera(camera_id)

    # -- zones ---------------------------------------------------------------

    def insert_zone(self, values: dict[str, Any]) -> sa.Row:
        return self._session.execute(
            sa.insert(zones).values(**values).returning(zones)
        ).one()

    def get_zone(self, zone_id: UUID) -> sa.Row | None:
        return self._session.execute(
            sa.select(zones).where(zones.c.id == zone_id)
        ).one_or_none()

    def zone_site(self, zone_id: UUID) -> UUID | None:
        """The site a zone belongs to, via its camera."""
        return self._session.execute(
            sa.select(cameras.c.site_id)
            .select_from(zones.join(cameras, zones.c.camera_id == cameras.c.id))
            .where(zones.c.id == zone_id)
        ).scalar_one_or_none()

    def list_zones(self, site_ids: Sequence[UUID]) -> Sequence[sa.Row]:
        return self._session.execute(
            sa.select(zones)
            .select_from(zones.join(cameras, zones.c.camera_id == cameras.c.id))
            .where(cameras.c.site_id.in_(list(site_ids)))
            .order_by(zones.c.name)
        ).all()

    def update_zone(self, zone_id: UUID, values: dict[str, Any]) -> sa.Row | None:
        return self._session.execute(
            sa.update(zones).where(zones.c.id == zone_id)
            .values(**values).returning(zones)
        ).one_or_none()

    def delete_zone(self, zone_id: UUID) -> bool:
        # RESTRICT foreign keys make this fail while rules or events
        # reference the zone — deletion never cascades into history
        # (DATABASE.md 3.2).
        result = self._session.execute(
            sa.delete(zones).where(zones.c.id == zone_id)
        )
        return result.rowcount == 1

    # -- detection rules -----------------------------------------------------

    def insert_rule(self, values: dict[str, Any]) -> sa.Row:
        return self._session.execute(
            sa.insert(detection_rules).values(**values).returning(detection_rules)
        ).one()

    def get_rule(self, rule_id: UUID) -> sa.Row | None:
        return self._session.execute(
            sa.select(detection_rules).where(detection_rules.c.id == rule_id)
        ).one_or_none()

    def rule_site(self, rule_id: UUID) -> UUID | None:
        return self._session.execute(
            sa.select(cameras.c.site_id)
            .select_from(
                detection_rules.join(zones, detection_rules.c.zone_id == zones.c.id)
                .join(cameras, zones.c.camera_id == cameras.c.id)
            )
            .where(detection_rules.c.id == rule_id)
        ).scalar_one_or_none()

    def list_rules(self, site_ids: Sequence[UUID]) -> Sequence[sa.Row]:
        return self._session.execute(
            sa.select(detection_rules)
            .select_from(
                detection_rules.join(zones, detection_rules.c.zone_id == zones.c.id)
                .join(cameras, zones.c.camera_id == cameras.c.id)
            )
            .where(cameras.c.site_id.in_(list(site_ids)))
            .order_by(detection_rules.c.created_at)
        ).all()

    def update_rule(self, rule_id: UUID, values: dict[str, Any]) -> sa.Row | None:
        return self._session.execute(
            sa.update(detection_rules)
            .where(detection_rules.c.id == rule_id)
            .values(**values)
            .returning(detection_rules)
        ).one_or_none()

    # -- lookups for ingest validation --------------------------------------

    def camera_site(self, camera_id: UUID) -> UUID | None:
        return self._session.execute(
            sa.select(cameras.c.site_id).where(cameras.c.id == camera_id)
        ).scalar_one_or_none()

    def zone_exists(self, zone_id: UUID) -> bool:
        return (
            self._session.execute(
                sa.select(sa.literal(1)).where(zones.c.id == zone_id)
            ).scalar_one_or_none()
            is not None
        )

    def rule_exists(self, rule_id: UUID) -> bool:
        return (
            self._session.execute(
                sa.select(sa.literal(1)).where(detection_rules.c.id == rule_id)
            ).scalar_one_or_none()
            is not None
        )

    def model_version_id(self, version: str) -> UUID | None:
        return self._session.execute(
            sa.select(model_versions.c.id).where(model_versions.c.version == version)
        ).scalar_one_or_none()

    # -- edge agents (WORKFLOW.md 7 gap 1) -----------------------------------

    def insert_agent(self, values: dict[str, Any]) -> sa.Row:
        return self._session.execute(
            sa.insert(agents).values(**values).returning(*_AGENT_PUBLIC)
        ).one()

    def list_agents(self, site_ids: Sequence[UUID]) -> Sequence[sa.Row]:
        return self._session.execute(
            sa.select(*_AGENT_PUBLIC)
            .where(agents.c.site_id.in_(list(site_ids)))
            .order_by(agents.c.name)
        ).all()

    # -- model versions (gate G1 evidence trail) -----------------------------

    def insert_model_version(self, values: dict[str, Any]) -> sa.Row:
        return self._session.execute(
            sa.insert(model_versions).values(**values).returning(model_versions)
        ).one()

    def get_model_version(self, model_version_id: UUID) -> sa.Row | None:
        return self._session.execute(
            sa.select(model_versions).where(model_versions.c.id == model_version_id)
        ).one_or_none()

    def list_model_versions(self) -> Sequence[sa.Row]:
        return self._session.execute(
            sa.select(model_versions).order_by(model_versions.c.version)
        ).all()

    def update_model_version(
        self, model_version_id: UUID, values: dict[str, Any]
    ) -> sa.Row | None:
        return self._session.execute(
            sa.update(model_versions)
            .where(model_versions.c.id == model_version_id)
            .values(**values)
            .returning(model_versions)
        ).one_or_none()

    # -- coverage gaps -------------------------------------------------------

    def upsert_coverage_gap(self, values: dict[str, Any]) -> None:
        """Idempotent on the edge-generated gap id (IF-E5: at-least-once
        delivery, dedup at the receiver). A retransmit may carry a later
        ended_at or detail; identity fields never change."""
        from sqlalchemy.dialects.postgresql import insert as pg_insert

        statement = pg_insert(coverage_gaps).values(**values)
        self._session.execute(
            statement.on_conflict_do_update(
                index_elements=[coverage_gaps.c.id],
                set_={
                    "ended_at": statement.excluded.ended_at,
                    "detail": statement.excluded.detail,
                },
            )
        )

    def gap_minutes_overlapping(
        self, *, site_id: UUID, window_from: datetime, window_to: datetime
    ) -> int:
        """Total minutes of coverage gap overlapping the window. A report
        without gap context is misleading: zero events may mean zero
        exceptions or zero watching (ARCHITECTURE.md 6.5)."""
        overlap_start = sa.func.greatest(coverage_gaps.c.started_at, window_from)
        overlap_end = sa.func.least(
            sa.func.coalesce(coverage_gaps.c.ended_at, window_to), window_to
        )
        seconds = sa.func.sum(
            sa.func.greatest(
                sa.func.extract("epoch", overlap_end - overlap_start), 0
            )
        )
        total = self._session.execute(
            sa.select(seconds).where(
                coverage_gaps.c.site_id == site_id,
                coverage_gaps.c.started_at <= window_to,
                sa.or_(
                    coverage_gaps.c.ended_at.is_(None),
                    coverage_gaps.c.ended_at >= window_from,
                ),
            )
        ).scalar_one()
        return int((total or 0) // 60)

    # -- agent config document (IF-X1) ---------------------------------------

    def agent_config_document(self, site_id: UUID) -> dict[str, Any] | None:
        """The pull-only config document for one site — ADR-008.

        Includes the SEALED camera credential and its key id: credentials
        are delivered encrypted and decrypted only at the edge
        (ARCHITECTURE.md 8.10). Only ACTIVE rules ship — an agent has no
        rules until a named user activated them (BR-001).
        """
        import base64

        site = self.get_site(site_id)
        if site is None:
            return None
        camera_rows = self._session.execute(
            sa.select(cameras).where(
                cameras.c.site_id == site_id, cameras.c.status != "disabled"
            ).order_by(cameras.c.name)
        ).all()
        zone_rows = self.list_zones([site_id])
        rule_rows = self._session.execute(
            sa.select(detection_rules)
            .select_from(
                detection_rules.join(zones, detection_rules.c.zone_id == zones.c.id)
                .join(cameras, zones.c.camera_id == cameras.c.id)
            )
            .where(cameras.c.site_id == site_id, detection_rules.c.is_active)
            .order_by(detection_rules.c.created_at)
        ).all()

        return {
            "config_version": site.config_version,
            "site": {
                "id": str(site.id),
                "name": site.name,
                "timezone": site.timezone,
            },
            "cameras": [
                {
                    "id": str(c.id),
                    "name": c.name,
                    "stream_profile": c.stream_profile,
                    "sample_rate_fps": float(c.sample_rate_fps),
                    "status": c.status,
                    "stream_url_sealed": base64.b64encode(
                        c.stream_url_encrypted
                    ).decode(),
                    "stream_url_key_id": c.stream_url_key_id,
                }
                for c in camera_rows
            ],
            "zones": [
                {
                    "id": str(z.id),
                    "camera_id": str(z.camera_id),
                    "name": z.name,
                    "polygon": z.polygon,
                }
                for z in zone_rows
            ],
            "rules": [
                {
                    "id": str(r.id),
                    "zone_id": str(r.zone_id),
                    "rule_type": r.rule_type,
                    "confidence_threshold": float(r.confidence_threshold),
                    "debounce_seconds": r.debounce_seconds,
                    "dwell_seconds": r.dwell_seconds,
                    "human_readable": r.human_readable,
                    "detection_class": r.detection_class,
                    "must_be_carried": r.must_be_carried,
                }
                for r in rule_rows
            ],
        }
