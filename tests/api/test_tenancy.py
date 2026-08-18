"""ADR-016 binding: identity assertion, quarantine, fail-closed refusal.

These are the API-layer rows of the bypass suite's tenancy section
(TRD 19.4): a request bound to tenant A handed a connection to tenant B
must abort and quarantine, and no unbound or non-active binding may serve.
"""

from __future__ import annotations

import uuid

import pytest

from guardian_lens.core.errors import TenantBindingError, TenantNotActiveError
from guardian_lens.db.urls import tenant_database_name
from guardian_lens.tenancy.registry import TenantRecord, TenantRegistry
from guardian_lens.tenancy.router import TenantRouter
from tests.api.conftest import bearer


@pytest.fixture
def registry(control_url: str) -> TenantRegistry:
    return TenantRegistry(control_url)


@pytest.mark.tenancy
def test_bind_asserts_tenant_identity_and_quarantines_on_mismatch(
    registry, tenant_slug, monkeypatch, control_url
):
    """Bypass row: bind to tenant A, hand it tenant B's database. The
    router must read tenant_identity, abort, and quarantine the pool —
    never retry, never serve."""
    imposter = TenantRecord(
        tenant_id=uuid.uuid4(),          # not the real tenant's id
        slug="imposter_tenant",          # not the database's slug
        status="active",
        database_name=tenant_database_name(tenant_slug),  # the REAL database
    )
    monkeypatch.setattr(registry, "get", lambda slug: imposter)
    router = TenantRouter(registry, __import__("os").environ["GL_TENANT_DB_URL"])

    with pytest.raises(TenantBindingError):
        with router.bind("imposter_tenant"):
            pytest.fail("a mismatched binding must never yield a session")

    # The pool is gone: nothing can quietly reuse a suspect connection.
    assert "imposter_tenant" not in router._engines


@pytest.mark.tenancy
def test_bind_succeeds_against_the_genuine_tenant(registry, tenant_slug):
    import os

    router = TenantRouter(registry, os.environ["GL_TENANT_DB_URL"])
    with router.bind(tenant_slug) as context:
        assert context.tenant_slug == tenant_slug
        # The session works and is bound to the asserted database.
        from sqlalchemy import text

        slug_in_db = context.session.execute(
            text("SELECT tenant_slug FROM tenant_identity")
        ).scalar_one()
        assert slug_in_db == tenant_slug


@pytest.mark.tenancy
@pytest.mark.parametrize("status", ["suspended", "drifted", "provisioning"])
def test_non_active_tenant_refuses_binding(registry, tenant_slug, monkeypatch, status):
    """Fail closed: FF-11's posture — a tenant whose enforcement state is
    unverified is refused, not merely alerted."""
    import os

    record = registry.get(tenant_slug)
    assert record is not None
    stale = TenantRecord(
        tenant_id=record.tenant_id,
        slug=record.slug,
        status=status,
        database_name=record.database_name,
    )
    monkeypatch.setattr(registry, "get", lambda slug: stale)
    router = TenantRouter(registry, os.environ["GL_TENANT_DB_URL"])
    with pytest.raises(TenantNotActiveError):
        with router.bind(tenant_slug):
            pytest.fail("suspended tenants must not bind")


@pytest.mark.tenancy
def test_unknown_tenant_fails_closed(registry):
    import os

    router = TenantRouter(registry, os.environ["GL_TENANT_DB_URL"])
    with pytest.raises(TenantNotActiveError):
        with router.bind("tenant_that_never_existed"):
            pytest.fail("unknown tenants must not bind")


@pytest.mark.tenancy
def test_token_naming_a_nonexistent_tenant_is_refused_at_http(app, client):
    """The tenant claim is server-derived from the token; a token naming a
    tenant the registry does not know fails closed as 403 — no fallback
    database, no unbound query (BACKEND_CODING_RULES 6.5)."""
    ghost_token = app.state.token_service.issue_access_token(
        uuid.uuid4(), "ghost_tenant", [("reviewer", uuid.uuid4())]
    )
    response = client.get("/api/v1/events", headers=bearer(ghost_token))
    assert response.status_code == 403


@pytest.mark.tenancy
def test_registry_cache_is_invalidated_explicitly(registry, tenant_slug):
    first = registry.get(tenant_slug)
    assert first is not None
    # Cached: same object within the TTL.
    assert registry.get(tenant_slug) is first
    registry.invalidate(tenant_slug)
    second = registry.get(tenant_slug)
    assert second is not first
    assert second == first  # same content, freshly loaded
    registry.invalidate_all()
    assert registry.get(tenant_slug) == first
