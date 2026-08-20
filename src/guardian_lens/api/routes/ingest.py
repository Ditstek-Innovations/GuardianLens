"""Ingest routes — MOD-6, agent principals only (TRD 10.3).

The event body is read RAW before validation: status, reviewer_id or
decided_at anywhere in it is the rule's 400 (BR-004), which must fire
before Pydantic's 422 could. A human token on any of these routes is 403 —
the write path into events is agent-only, exactly as the decision path is
human-only.
"""

from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, Depends, Request, Response

from guardian_lens.api.dependencies.auth import require_agent
from guardian_lens.api.dependencies.tenant import get_tenant_context
from guardian_lens.core.errors import MalformedRequestError
from guardian_lens.core.principal import AgentPrincipal
from guardian_lens.guards.reviewer_attribution import ReviewerAttributionGuard
from guardian_lens.schemas.events import (
    AgentHealthRequest,
    AgentHealthResponse,
    CoverageGapRequest,
    EventIngestRequest,
    IngestResponse,
)
from guardian_lens.schemas.validation import require_json_object, validate_model
from guardian_lens.services.ingest import EventIngestService
from guardian_lens.tenancy.context import TenantContext

router = APIRouter(tags=["ingest"])


async def raw_json_body(request: Request) -> dict[str, Any]:
    """The raw body as a JSON object, before any model validation."""
    try:
        data = json.loads(await request.body())
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise MalformedRequestError("request body is not valid JSON") from exc
    return require_json_object(data)


def _service(request: Request, context: TenantContext) -> EventIngestService:
    settings = request.app.state.settings
    return EventIngestService(
        context,
        request.app.state.evidence_store,
        evidence_max_bytes=settings.evidence_max_bytes,
        clock_skew_tolerance_seconds=settings.clock_skew_tolerance_seconds,
    )


@router.post("/events", response_model=IngestResponse, status_code=201)
def ingest_event(
    request: Request,
    response: Response,
    body: dict[str, Any] = Depends(raw_json_body),
    agent: AgentPrincipal = Depends(require_agent),
    context: TenantContext = Depends(get_tenant_context),
) -> IngestResponse:
    # BR-004 before anything else: server-owned fields are a 400, not 422.
    ReviewerAttributionGuard.ensure_no_client_attribution(body.keys())
    payload = validate_model(EventIngestRequest, body)

    outcome = _service(request, context).ingest(payload, agent)
    if not outcome.created:
        # Idempotent duplicate: the existing resource, 200 (TRD 10.3).
        response.status_code = 200
    return IngestResponse(
        id=outcome.row.id,
        event_id=outcome.row.event_id,
        status=outcome.row.status,
        received_at=outcome.row.received_at,
    )


@router.post("/agents/health", response_model=AgentHealthResponse)
def agent_health(
    body: AgentHealthRequest,
    request: Request,
    agent: AgentPrincipal = Depends(require_agent),
    context: TenantContext = Depends(get_tenant_context),
) -> AgentHealthResponse:
    skew = _service(request, context).record_health(
        agent,
        sent_at=body.sent_at,
        applied_config_version=body.applied_config_version,
        agent_version=body.agent_version,
        review_block=(
            [item.model_dump(mode="json") for item in body.review_block]
            if body.review_block is not None
            else None
        ),
    )
    return AgentHealthResponse(clock_skew_ms=skew)


@router.post("/coverage-gaps", status_code=200)
def report_coverage_gap(
    body: CoverageGapRequest,
    request: Request,
    agent: AgentPrincipal = Depends(require_agent),
    context: TenantContext = Depends(get_tenant_context),
) -> dict[str, str]:
    _service(request, context).record_coverage_gap(
        agent,
        gap_id=body.id,
        camera_id=body.camera_id,
        started_at=body.started_at,
        ended_at=body.ended_at,
        reason=body.reason,
        detail=body.detail,
    )
    return {"status": "recorded"}
