"""Tenant binding dependency — the request's single door to tenant data.

Resolves the tenant from the AUTHENTICATED PRINCIPAL's token claim — never
from a header, path or body parameter (ARCHITECTURE.md 8.9.2) — and yields
a TenantContext whose session has passed the tenant_identity assertion.
Every tenant-scoped route receives its session from here and nowhere else,
so no unbound query path exists.
"""

from __future__ import annotations

from collections.abc import Iterator

from fastapi import Depends, Request

from guardian_lens.api.dependencies.auth import get_principal
from guardian_lens.core.logging import tenant_var
from guardian_lens.core.principal import Principal
from guardian_lens.tenancy.context import TenantContext
from guardian_lens.tenancy.router import TenantRouter

__all__ = ["get_tenant_context"]


def get_tenant_context(
    request: Request,
    principal: Principal = Depends(get_principal),
) -> Iterator[TenantContext]:
    router: TenantRouter = request.app.state.tenant_router
    tenant_var.set(principal.tenant_slug)
    with router.bind(principal.tenant_slug) as context:
        try:
            yield context
        except BaseException:
            # Whatever failed, nothing half-done leaves this request: the
            # session's transaction is discarded before the error surfaces.
            # (This is the rollback half of BR-AU-03 — services commit
            # explicitly, so an audit failure arrives here with the
            # decision still uncommitted.)
            context.session.rollback()
            raise
