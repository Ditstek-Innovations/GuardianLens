"""Reporting routes — MOD-9 basic (TRD 10.5)."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response

from guardian_lens.api.dependencies.auth import require_queue_read
from guardian_lens.api.dependencies.tenant import get_tenant_context
from guardian_lens.core.errors import ValidationFailureError
from guardian_lens.core.principal import HumanPrincipal
from guardian_lens.services.reporting import GROUP_BY_CHOICES, ReportingService
from guardian_lens.tenancy.context import TenantContext

router = APIRouter(prefix="/reports", tags=["reports"])


def _checked_group_by(group_by: str) -> str:
    if group_by not in GROUP_BY_CHOICES:
        raise ValidationFailureError(
            f"group_by must be one of {sorted(GROUP_BY_CHOICES)}",
            field="group_by",
        )
    return group_by


@router.get("/summary")
def report_summary(
    site_id: UUID = Query(),
    from_: datetime = Query(alias="from"),
    to: datetime = Query(),
    group_by: str = Query(default="zone"),
    principal: HumanPrincipal = Depends(require_queue_read),
    context: TenantContext = Depends(get_tenant_context),
) -> dict[str, Any]:
    return ReportingService(context).summary(
        principal=principal,
        site_id=site_id,
        occurred_from=from_,
        occurred_to=to,
        group_by=_checked_group_by(group_by),
    ).payload


@router.get("/export")
def report_export(
    site_id: UUID = Query(),
    from_: datetime = Query(alias="from"),
    to: datetime = Query(),
    group_by: str = Query(default="zone"),
    principal: HumanPrincipal = Depends(require_queue_read),
    context: TenantContext = Depends(get_tenant_context),
) -> Response:
    # CSV at MVP. The provenance header — period, generating user, basis —
    # travels inside the file (BR-R-02).
    content = ReportingService(context).export_csv(
        principal=principal,
        site_id=site_id,
        occurred_from=from_,
        occurred_to=to,
        group_by=_checked_group_by(group_by),
    )
    return Response(
        content=content,
        media_type="text/csv",
        headers={
            "Content-Disposition": "attachment; filename=guardian-lens-report.csv"
        },
    )
