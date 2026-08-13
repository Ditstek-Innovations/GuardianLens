"""Review routes — MOD-7 (TRD 10.4).

The queue and detail reads are scoped at the repository level; evidence
retrieval adds the object-level check; and the decision endpoint hands the
RAW body to DecisionService, which runs ARCHITECTURE.md 5.5's D2 ladder in
order. There is NO bulk decision route in this module or anywhere else —
its absence is bypass-suite row 6 (TRD 19.4).
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, Response

from guardian_lens.api.dependencies.auth import (
    require_decide_role,
    require_queue_read,
)
from guardian_lens.api.dependencies.tenant import get_tenant_context
from guardian_lens.api.routes.ingest import raw_json_body
from guardian_lens.core.errors import NotFoundError
from guardian_lens.core.principal import HumanPrincipal
from guardian_lens.repositories.events import EventRepository
from guardian_lens.repositories.evidence import EvidenceStore
from guardian_lens.schemas.events import (
    DecisionResponse,
    EventDetail,
    QueueCamera,
    QueueItem,
    QueueResponse,
    QueueRule,
    QueueZone,
)
from guardian_lens.services.audit import AuditService
from guardian_lens.services.decision import DecisionService
from guardian_lens.repositories.audit import AuditRepository
from guardian_lens.tenancy.context import TenantContext

router = APIRouter(tags=["review"])


def _evidence_url(event_pk: UUID, evidence_state: str) -> str | None:
    if evidence_state != "present":
        return None
    return f"/api/v1/events/{event_pk}/evidence"


@router.get("/events", response_model=QueueResponse)
def list_events(
    principal: HumanPrincipal = Depends(require_queue_read),
    context: TenantContext = Depends(get_tenant_context),
    status: str = Query(default="unverified"),
    site_id: UUID | None = Query(default=None),
    camera_id: UUID | None = Query(default=None),
    zone_id: UUID | None = Query(default=None),
    rule_id: UUID | None = Query(default=None),
    from_: datetime | None = Query(default=None, alias="from"),
    to: datetime | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    cursor: str | None = Query(default=None),
) -> QueueResponse:
    repository = EventRepository(context.session)
    rows, next_cursor, depth = repository.queue_page(
        # The permitted set comes from the token; query filters can only
        # narrow it (TRD 12.3 enforcement point 2).
        site_ids=principal.site_ids(),
        status=status,
        limit=limit,
        cursor=cursor,
        site_id=site_id,
        camera_id=camera_id,
        zone_id=zone_id,
        rule_id=rule_id,
        occurred_from=from_,
        occurred_to=to,
    )
    return QueueResponse(
        items=[
            QueueItem(
                id=row.id,
                camera=QueueCamera(id=row.camera_id, name=row.camera_name),
                zone=QueueZone(id=row.zone_id, name=row.zone_name),
                rule=QueueRule(
                    human_readable=row.rule_human_readable
                    or (row.rule_snapshot or {}).get("human_readable")
                ),
                source=row.source,
                confidence=float(row.confidence)
                if row.confidence is not None
                else None,
                occurred_at=row.occurred_at,
                status=row.status,
                evidence_url=_evidence_url(row.id, row.evidence_state),
                version=row.version,
            )
            for row in rows
        ],
        queue_depth=depth,
        next_cursor=next_cursor,
    )


@router.get("/events/{event_pk}", response_model=EventDetail)
def get_event(
    event_pk: UUID,
    principal: HumanPrincipal = Depends(require_queue_read),
    context: TenantContext = Depends(get_tenant_context),
) -> EventDetail:
    row = EventRepository(context.session).get_scoped(
        event_pk, principal.site_ids()
    )
    if row is None:
        # Out of scope reads exactly like absent: existence must not leak
        # across the scope boundary.
        raise NotFoundError("event not found")
    return EventDetail(
        id=row.id,
        event_id=row.event_id,
        camera_id=row.camera_id,
        zone_id=row.zone_id,
        rule_id=row.rule_id,
        rule_snapshot=row.rule_snapshot,
        source=row.source,
        confidence=float(row.confidence) if row.confidence is not None else None,
        occurred_at=row.occurred_at,
        received_at=row.received_at,
        status=row.status,
        evidence_url=_evidence_url(row.id, row.evidence_state),
        evidence_state=row.evidence_state,
        decision_type=row.decision_type,
        rejection_reason=row.rejection_reason,
        version=row.version,
    )


@router.get("/events/{event_pk}/evidence")
def get_evidence(
    event_pk: UUID,
    request: Request,
    principal: HumanPrincipal = Depends(require_queue_read),
    context: TenantContext = Depends(get_tenant_context),
) -> Response:
    # Object-level authorisation (TRD 12.3 point 3): the event row, in
    # scope, is what authorises the object read — possession of a key or
    # URL grants nothing (BACKEND_CODING_RULES 20).
    row = EventRepository(context.session).get_scoped(
        event_pk, principal.site_ids()
    )
    if row is None or row.evidence_state != "present" or row.evidence_ref is None:
        raise NotFoundError("evidence not found")
    store: EvidenceStore = request.app.state.evidence_store
    content = store.get(row.evidence_ref)
    if content is None:
        raise NotFoundError("evidence not found")
    return Response(
        content=content,
        media_type="image/jpeg",
        # Immutable content; private caching is safe and helps QS-3.
        headers={"Cache-Control": "private, max-age=300"},
    )


@router.post("/events/{event_pk}/decision", response_model=DecisionResponse)
def decide_event(
    event_pk: UUID,
    request: Request,
    body: dict[str, Any] = Depends(raw_json_body),
    principal: HumanPrincipal = Depends(require_decide_role),
    context: TenantContext = Depends(get_tenant_context),
) -> DecisionResponse:
    service = DecisionService(
        context, AuditService(AuditRepository(context.session))
    )
    result = service.apply_decision(
        event_pk=event_pk,
        principal=principal,
        body=body,
        ip_address=request.client.host if request.client else None,
    )
    return DecisionResponse(**result)
