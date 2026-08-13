"""Audit read route — MOD-8.

GET only, forever: any DELETE or PATCH on /audit is an endpoint that must
never exist (TRD 10.9, BR-AU-01). Read access follows the TRD 12.3 matrix
— safety_manager, site_admin and auditor.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from guardian_lens.api.dependencies.auth import require_audit_read
from guardian_lens.api.dependencies.tenant import get_tenant_context
from guardian_lens.core.principal import HumanPrincipal
from guardian_lens.repositories.audit import AuditRepository
from guardian_lens.schemas.audit import AuditEntry, AuditPage
from guardian_lens.tenancy.context import TenantContext

router = APIRouter(tags=["audit"])


@router.get("/audit", response_model=AuditPage)
def read_audit(
    principal: HumanPrincipal = Depends(require_audit_read),
    context: TenantContext = Depends(get_tenant_context),
    entity_type: str | None = Query(default=None),
    entity_id: UUID | None = Query(default=None),
    from_: datetime | None = Query(default=None, alias="from"),
    to: datetime | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    cursor: str | None = Query(default=None),
) -> AuditPage:
    after_id = int(cursor) if cursor and cursor.isdigit() else None
    rows = AuditRepository(context.session).page(
        limit=limit,
        after_id=after_id,
        entity_type=entity_type,
        entity_id=entity_id,
        occurred_from=from_,
        occurred_to=to,
    )
    items = [
        AuditEntry(
            id=row.id,
            actor_user_id=row.actor_user_id,
            actor_agent_id=row.actor_agent_id,
            action=row.action,
            entity_type=row.entity_type,
            entity_id=row.entity_id,
            entity_key=row.entity_key,
            before_state=row.before_state,
            after_state=row.after_state,
            occurred_at=row.occurred_at,
        )
        for row in rows
    ]
    next_cursor = str(items[-1].id) if len(items) == limit else None
    return AuditPage(items=items, next_cursor=next_cursor)
