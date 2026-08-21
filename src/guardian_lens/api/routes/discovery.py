"""Camera discovery routes - scan network, list candidates, import cameras.

POST   /api/v1/discovery/scan              Trigger network scan for cameras
GET    /api/v1/discovery/scans/{scan_id}  Get scan status and progress
GET    /api/v1/discovery/candidates       List discovered camera candidates
POST   /api/v1/discovery/candidates/{id}/adopt  Import candidate as camera
DELETE /api/v1/discovery/candidates/{id}  Discard candidate
"""

from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request

from guardian_lens.api.dependencies.auth import require_site_admin
from guardian_lens.api.dependencies.tenant import get_tenant_context
from guardian_lens.core.principal import HumanPrincipal
from guardian_lens.repositories.camera_discovery import (
    CameraDiscoveryRepository,
)
from guardian_lens.schemas.config import (
    CameraDiscoveryBulkImportResponse,
    CameraDiscoveryCandidateResponse,
    CameraDiscoveryImportRequest,
    CameraResponse,
    DiscoveryScanResponse,
)
from guardian_lens.services.camera_discovery import (
    RTSPProbeService,
    camera_rtsp_url,
)
from guardian_lens.services.configuration import ConfigurationService
from guardian_lens.repositories.audit import AuditRepository
from guardian_lens.services.audit import AuditService
from guardian_lens.tenancy.context import TenantContext

router = APIRouter(prefix="/discovery", tags=["discovery"])


def _config_service(
    request: Request, context: TenantContext
) -> ConfigurationService:
    return ConfigurationService(
        context,
        AuditService(AuditRepository(context.session)),
        request.app.state.credential_sealer,
    )


def _ip(request: Request) -> str | None:
    return request.client.host if request.client else None


_FULL_FRAME = [[0.0, 0.0], [1.0, 0.0], [1.0, 1.0], [0.0, 1.0]]
def _adopt_candidate(
    *,
    candidate: dict,
    name: str,
    location_description: str | None,
    stream_profile: str,
    sample_rate_fps: float,
    rtsp_path: str | None,
    request: Request,
    context: TenantContext,
    principal: HumanPrincipal,
    rtsp_username: str | None = None,
    rtsp_password: str | None = None,
) -> Any:
    """Seal the candidate's IP/path (and optional camera login) as the stream URL."""
    path = rtsp_path or candidate.get("default_rtsp_path")
    if not path:
        raise HTTPException(status_code=400, detail="No RTSP path selected")
    try:
        stream_url = camera_rtsp_url(
            candidate["ip_address"],
            candidate["port"],
            path,
            username=rtsp_username,
            password=rtsp_password,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    config_service = _config_service(request, context)
    camera_row = config_service.create_camera(
        principal=principal,
        site_id=candidate["site_id"],
        name=name,
        stream_url=stream_url,
        location_description=location_description,
        stream_profile=stream_profile,
        sample_rate_fps=sample_rate_fps,
        ip_address=_ip(request),
    )
    config_service.create_zone(
        principal=principal,
        camera_id=camera_row.id,
        name=f"{name} zone",
        polygon=_FULL_FRAME,
        ip_address=_ip(request),
    )
    CameraDiscoveryRepository(context.session).mark_candidate_imported(
        candidate["id"], camera_row.id
    )
    context.session.commit()
    return camera_row


@router.post("/scan", response_model=DiscoveryScanResponse, status_code=202)
async def start_discovery_scan(
    subnet: str,
    site_id: UUID,
    background_tasks: BackgroundTasks,
    request: Request,
    principal: HumanPrincipal = Depends(require_site_admin),
    context: TenantContext = Depends(get_tenant_context),
) -> DiscoveryScanResponse:
    """Start a network scan for cameras in the specified subnet.

    Returns immediately with scan_id; actual scanning happens in background.
    Poll /discovery/scans/{scan_id} to check progress.

    Args:
        subnet: CIDR notation (e.g., "192.168.1.0/24")
        site_id: Site to associate discovered cameras with
    """
    scan_id = uuid4()
    repo = CameraDiscoveryRepository(context.session)

    # Create scan record
    repo.create_scan(scan_id, site_id)
    context.session.commit()

    # Add background task to perform actual scan
    background_tasks.add_task(
        _perform_discovery_scan,
        scan_id,
        subnet,
        site_id,
        principal.tenant_slug,
        request.app.state.tenant_router,
    )

    return DiscoveryScanResponse(
        id=scan_id,
        site_id=site_id,
        started_at=datetime.utcnow(),
        completed_at=None,
        scan_method="rtsp_probe",
        cameras_found=0,
        status="in_progress",
    )


async def _perform_discovery_scan(
    scan_id: UUID,
    subnet: str,
    site_id: UUID,
    tenant_slug: str,
    tenant_router: Any,
) -> None:
    """Background task to perform the actual camera discovery scan."""
    service = RTSPProbeService()
    try:
        discovered = await service.scan_subnet(subnet)
    except Exception as e:
        import logging
        logging.error(f'Scan failed: {e}')
        discovered = []
        
    with tenant_router.bind(tenant_slug) as context:
        repo = CameraDiscoveryRepository(context.session)
        try:
            # Store results in database
            for camera in discovered:
                candidate_id = uuid4()
                repo.create_candidate(
                    candidate_id=candidate_id,
                    scan_id=scan_id,
                    site_id=site_id,
                    ip_address=camera.ip_address,
                    port=camera.port,
                    rtsp_paths=[camera.rtsp_path],
                    default_rtsp_path=camera.rtsp_path,
                    resolution=camera.resolution,
                    codec=camera.codec,
                    model=camera.model,
                    manufacturer=camera.manufacturer,
                )

            # Update scan status
            repo.update_scan_status(
                scan_id,
                status="completed",
                cameras_found=len(discovered),
            )
            context.session.commit()

        except Exception as e:
            # Update scan status to failed
            context.session.rollback()
            repo.update_scan_status(scan_id, status="failed")
            context.session.commit()


@router.get("/scans/{scan_id}", response_model=DiscoveryScanResponse)
async def get_scan_status(
    scan_id: UUID,
    principal: HumanPrincipal = Depends(require_site_admin),
    context: TenantContext = Depends(get_tenant_context),
) -> DiscoveryScanResponse:
    """Get the status and progress of a discovery scan.

    Returns current status: in_progress, completed, or failed.
    """
    repo = CameraDiscoveryRepository(context.session)
    scan = repo.get_scan(scan_id)

    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")

    return DiscoveryScanResponse(
        id=scan["id"],
        site_id=scan["site_id"],
        started_at=scan["started_at"],
        completed_at=scan["completed_at"],
        scan_method=scan["scan_method"],
        cameras_found=scan["cameras_found"],
        status=scan["status"],
    )


@router.get("/candidates", response_model=list[CameraDiscoveryCandidateResponse])
async def list_candidates(
    site_id: UUID,
    status: str | None = None,
    principal: HumanPrincipal = Depends(require_site_admin),
    context: TenantContext = Depends(get_tenant_context),
) -> list[CameraDiscoveryCandidateResponse]:
    """List discovered camera candidates awaiting user selection.

    Args:
        site_id: Filter candidates for this site
        status: Filter by status (verified, unreachable, error, imported)
    """
    repo = CameraDiscoveryRepository(context.session)
    candidates = repo.get_candidates(site_id, status=status)

    return [
        CameraDiscoveryCandidateResponse(
            id=c["id"],
            site_id=c["site_id"],
            scan_id=c["scan_id"],
            ip_address=c["ip_address"],
            hostname=c.get("hostname"),
            port=c["port"],
            model=c.get("model"),
            manufacturer=c.get("manufacturer"),
            rtsp_paths=c.get("rtsp_paths", []),
            default_rtsp_path=c.get("default_rtsp_path"),
            resolution=c.get("resolution"),
            codec=c.get("codec"),
            status=c["status"],
            verified_at=c.get("verified_at"),
            imported_at=c.get("imported_at"),
            discovered_at=c["discovered_at"],
            created_at=c["created_at"],
        )
        for c in candidates
    ]


@router.post(
    "/candidates/{candidate_id}/adopt",
    response_model=CameraResponse,
    status_code=201,
)
async def import_candidate(
    candidate_id: UUID,
    body: CameraDiscoveryImportRequest,
    request: Request,
    principal: HumanPrincipal = Depends(require_site_admin),
    context: TenantContext = Depends(get_tenant_context),
) -> CameraResponse:
    """Import a discovered camera candidate as an actual camera.

    Constructs the RTSP stream URL from the candidate's IP and selected path,
    then creates a camera via the standard create_camera flow.

    Args:
        candidate_id: The discovered candidate to import
        body: Import configuration (name, location, stream profile, etc)
    """
    repo = CameraDiscoveryRepository(context.session)
    candidate = repo.get_candidate(candidate_id)

    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")
    if candidate.get("imported_at") is not None:
        raise HTTPException(status_code=409, detail="Candidate already imported")

    camera_row = _adopt_candidate(
        candidate=candidate,
        name=body.name,
        location_description=body.location_description,
        stream_profile=body.stream_profile,
        sample_rate_fps=body.sample_rate_fps,
        rtsp_path=body.rtsp_path,
        rtsp_username=body.rtsp_username,
        rtsp_password=body.rtsp_password,
        request=request,
        context=context,
        principal=principal,
    )
    return CameraResponse.model_validate(camera_row._mapping)


@router.post(
    "/candidates/adopt-pending",
    response_model=CameraDiscoveryBulkImportResponse,
)
async def import_pending_candidates(
    site_id: UUID,
    request: Request,
    principal: HumanPrincipal = Depends(require_site_admin),
    context: TenantContext = Depends(get_tenant_context),
) -> CameraDiscoveryBulkImportResponse:
    """Register every pending scanned camera.

    An auth-required camera is registered with its anonymous RTSP endpoint.
    It remains unavailable until an administrator adds the full credential
    later through Configuration → Cameras → Replace credential.
    """
    repo = CameraDiscoveryRepository(context.session)
    pending = [
        row
        for row in repo.get_candidates(site_id)
        if row.get("imported_at") is None and row.get("status") != "imported"
    ]
    imported = 0
    already = 0
    for candidate in pending:
        name = f"{candidate.get('model') or 'Camera'} - {candidate['ip_address']}"
        _adopt_candidate(
            candidate=candidate,
            name=name,
            location_description=None,
            stream_profile="secondary",
            sample_rate_fps=2.0,
            rtsp_path=None,
            request=request,
            context=context,
            principal=principal,
        )
        imported += 1
    return CameraDiscoveryBulkImportResponse(
        imported_count=imported,
        skipped_auth_required=0,
        skipped_already_imported=already,
    )


@router.delete("/candidates/{candidate_id}", status_code=204)
async def discard_candidate(
    candidate_id: UUID,
    principal: HumanPrincipal = Depends(require_site_admin),
    context: TenantContext = Depends(get_tenant_context),
) -> None:
    """Discard a discovered camera candidate (delete it).

    Candidate can be re-discovered in a future scan.
    """
    repo = CameraDiscoveryRepository(context.session)
    candidate = repo.get_candidate(candidate_id)

    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")

    repo.delete_candidate(candidate_id)
    context.session.commit()
