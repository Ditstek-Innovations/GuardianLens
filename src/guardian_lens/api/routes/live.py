"""Authenticated near-live camera previews without exposing RTSP URLs."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Request, Response

from guardian_lens.api.dependencies.auth import require_agent, require_queue_read
from guardian_lens.api.dependencies.tenant import get_tenant_context
from guardian_lens.core.errors import (
    MalformedRequestError,
    NotFoundError,
    PayloadTooLargeError,
)
from guardian_lens.core.principal import AgentPrincipal, HumanPrincipal
from guardian_lens.repositories.config import ConfigRepository
from guardian_lens.tenancy.context import TenantContext

router = APIRouter(tags=["live"])

_MAX_PREVIEW_BYTES = 2 * 1024 * 1024


def _camera_in_site(
    context: TenantContext, camera_id: UUID, site_ids: set[UUID] | frozenset[UUID]
):
    camera = ConfigRepository(context.session).get_camera(camera_id)
    if camera is None or camera.site_id not in site_ids:
        raise NotFoundError("camera not found")
    return camera


@router.post("/agents/cameras/{camera_id}/preview", status_code=204)
async def publish_preview(
    camera_id: UUID,
    request: Request,
    agent: AgentPrincipal = Depends(require_agent),
    context: TenantContext = Depends(get_tenant_context),
) -> Response:
    _camera_in_site(context, camera_id, {agent.site_id})
    if request.headers.get("content-type", "").split(";", 1)[0] != "image/jpeg":
        raise MalformedRequestError("preview must be image/jpeg")
    content = await request.body()
    if len(content) > _MAX_PREVIEW_BYTES:
        raise PayloadTooLargeError("preview exceeds 2 MiB")
    if len(content) < 4 or not content.startswith(b"\xff\xd8") or not content.endswith(b"\xff\xd9"):
        raise MalformedRequestError("preview is not a valid JPEG envelope")
    captured_raw = request.headers.get("x-captured-at", "")
    try:
        captured_at = datetime.fromisoformat(captured_raw.replace("Z", "+00:00"))
    except ValueError as exc:
        raise MalformedRequestError("X-Captured-At must be an ISO-8601 timestamp") from exc
    if captured_at.tzinfo is None:
        raise MalformedRequestError("X-Captured-At must include a timezone")
    request.app.state.live_preview_store.put(
        agent.tenant_slug, camera_id, content, captured_at
    )
    return Response(status_code=204)


@router.get("/cameras/{camera_id}/live-frame")
def live_frame(
    camera_id: UUID,
    request: Request,
    principal: HumanPrincipal = Depends(require_queue_read),
    context: TenantContext = Depends(get_tenant_context),
) -> Response:
    _camera_in_site(context, camera_id, principal.site_ids())
    preview = request.app.state.live_preview_store.get(
        principal.tenant_slug, camera_id
    )
    if preview is None:
        raise NotFoundError("live preview is not available yet")
    return Response(
        content=preview.content,
        media_type="image/jpeg",
        headers={
            "Cache-Control": "private, no-store",
            "X-Captured-At": preview.captured_at.isoformat(),
        },
    )
