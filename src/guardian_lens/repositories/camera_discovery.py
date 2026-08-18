"""Camera discovery repository - database access for scan candidates."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from guardian_lens.repositories.tables import (
    camera_discovery_candidates,
    camera_discovery_scans,
)


class CameraDiscoveryRepository:
    """Repository for camera discovery scans and candidates."""

    def __init__(self, session: Session):
        self.session = session

    def create_scan(
        self,
        scan_id: UUID,
        site_id: UUID,
        method: str = "rtsp_probe",
    ) -> dict:
        """Create a new discovery scan record."""
        stmt = camera_discovery_scans.insert().values(
            id=scan_id,
            site_id=site_id,
            started_at=datetime.utcnow(),
            scan_method=method,
            status="in_progress",
            cameras_found=0,
        )
        self.session.execute(stmt)
        self.session.flush()

        # Return the created scan
        select_stmt = (
            sa.select(camera_discovery_scans)
            .where(camera_discovery_scans.c.id == scan_id)
        )
        row = self.session.execute(select_stmt).first()
        return dict(row._mapping) if row else {}

    def update_scan_status(
        self,
        scan_id: UUID,
        status: str,
        cameras_found: int | None = None,
    ) -> None:
        """Update scan status and optionally camera count."""
        values = {"status": status}
        if cameras_found is not None:
            values["cameras_found"] = cameras_found

        if status == "completed":
            values["completed_at"] = datetime.utcnow()

        stmt = (
            camera_discovery_scans.update()
            .where(camera_discovery_scans.c.id == scan_id)
            .values(**values)
        )
        self.session.execute(stmt)
        self.session.flush()

    def create_candidate(
        self,
        candidate_id: UUID,
        scan_id: UUID,
        site_id: UUID,
        ip_address: str,
        port: int,
        rtsp_paths: list[str],
        default_rtsp_path: str | None = None,
        resolution: str | None = None,
        codec: str | None = None,
        model: str | None = None,
        manufacturer: str | None = None,
    ) -> dict:
        """Create a discovered camera candidate."""
        stmt = pg_insert(camera_discovery_candidates).values(
            id=candidate_id,
            scan_id=scan_id,
            site_id=site_id,
            discovered_at=datetime.utcnow(),
            ip_address=ip_address,
            port=port,
            rtsp_paths=rtsp_paths,
            default_rtsp_path=default_rtsp_path,
            resolution=resolution,
            codec=codec,
            model=model,
            manufacturer=manufacturer,
            status="verified",
            verified_at=datetime.utcnow(),
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

        stmt = stmt.on_conflict_do_update(
            constraint="uq_candidate_site_ip_port",
            set_={
                "scan_id": stmt.excluded.scan_id,
                "rtsp_paths": stmt.excluded.rtsp_paths,
                "default_rtsp_path": stmt.excluded.default_rtsp_path,
                "resolution": stmt.excluded.resolution,
                "codec": stmt.excluded.codec,
                "model": stmt.excluded.model,
                "manufacturer": stmt.excluded.manufacturer,
                "status": "verified",
                "verified_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
            }
        )
        
        self.session.execute(stmt)
        self.session.flush()

        # Return the created candidate
        select_stmt = (
            sa.select(camera_discovery_candidates)
            .where(camera_discovery_candidates.c.id == candidate_id)
        )
        row = self.session.execute(select_stmt).first()
        return dict(row._mapping) if row else {}

    def get_scan(self, scan_id: UUID) -> dict | None:
        """Get scan by ID."""
        stmt = sa.select(camera_discovery_scans).where(
            camera_discovery_scans.c.id == scan_id
        )
        row = self.session.execute(stmt).first()
        return dict(row._mapping) if row else None

    def get_candidates(
        self,
        site_id: UUID,
        status: str | None = None,
        scan_id: UUID | None = None,
    ) -> list[dict]:
        """Get candidates for a site, optionally filtered by status/scan."""
        stmt = sa.select(camera_discovery_candidates).where(
            camera_discovery_candidates.c.site_id == site_id
        )

        if status:
            stmt = stmt.where(camera_discovery_candidates.c.status == status)

        if scan_id:
            stmt = stmt.where(camera_discovery_candidates.c.scan_id == scan_id)

        stmt = stmt.order_by(camera_discovery_candidates.c.discovered_at.desc())

        rows = self.session.execute(stmt).fetchall()
        return [dict(row._mapping) for row in rows]

    def get_candidate(self, candidate_id: UUID) -> dict | None:
        """Get a specific candidate."""
        stmt = sa.select(camera_discovery_candidates).where(
            camera_discovery_candidates.c.id == candidate_id
        )
        row = self.session.execute(stmt).first()
        return dict(row._mapping) if row else None

    def mark_candidate_imported(
        self,
        candidate_id: UUID,
        camera_id: UUID,
    ) -> None:
        """Mark a candidate as imported and link to camera."""
        stmt = (
            camera_discovery_candidates.update()
            .where(camera_discovery_candidates.c.id == candidate_id)
            .values(
                imported_at=datetime.utcnow(),
                imported_camera_id=camera_id,
                status="imported",
                updated_at=datetime.utcnow(),
            )
        )
        self.session.execute(stmt)
        self.session.flush()

    def delete_candidate(self, candidate_id: UUID) -> None:
        """Delete a candidate."""
        stmt = camera_discovery_candidates.delete().where(
            camera_discovery_candidates.c.id == candidate_id
        )
        self.session.execute(stmt)
        self.session.flush()
