"""Tenant router — binding, per-tenant pools, and the identity assertion.

ARCHITECTURE.md 8.9.1: every request is bound to exactly one tenant before
any query, and step 7 — the control that matters — asserts that the
connection just acquired belongs to the tenant it was bound for, by reading
the single-row tenant_identity table BEFORE executing anything else.

Without that assertion a stale registry cache, a recycled pool, a copied
connection string or a restore into the wrong target silently writes one
customer's events into another customer's database — and nothing in the
data can contradict it, because in a silo model there is no tenant_id
column on the rows (DATABASE.md 1.4.1).

On mismatch: ABORT, alert, quarantine the pool. A mis-routed connection is
a P1 incident, never a retry.
"""

from __future__ import annotations

import logging
from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from guardian_lens.core.errors import TenantBindingError, TenantNotActiveError
from guardian_lens.core.logging import get_logger, log_event
from guardian_lens.db.urls import sqlalchemy_url, with_database
from guardian_lens.tenancy.context import TenantContext
from guardian_lens.tenancy.registry import TenantRecord, TenantRegistry

__all__ = ["TenantRouter"]

_log = get_logger("guardian_lens.tenancy")


class TenantRouter:
    """Central owner of every tenant engine and pool.

    Only this class creates tenant engines (BACKEND_CODING_RULES 6.3).
    Pools are per tenant; a pooled connection is never handed to a request
    bound to a different tenant, because each pool serves exactly one slug.
    """

    def __init__(
        self,
        registry: TenantRegistry,
        base_url: str,
        *,
        pool_size: int = 5,
        max_overflow: int = 5,
    ) -> None:
        self._registry = registry
        self._base_url = base_url
        self._pool_size = pool_size
        self._max_overflow = max_overflow
        self._engines: dict[str, Engine] = {}

    @contextmanager
    def bind(self, slug: str) -> Iterator[TenantContext]:
        """Bind to one tenant and yield an asserted session.

        The slug MUST come from the authenticated principal's token claim —
        never from a header, path or body parameter (ARCHITECTURE.md 8.9.2).
        Both callers (the request dependency and login, where the claim is
        the directory resolution) satisfy this.
        """
        record = self._registry.get(slug)
        if record is None or not record.is_active:
            # Fail closed. Unknown, suspended, drifted and deprovisioned all
            # refuse binding — serving a tenant whose rule enforcement is
            # unverified is worse than serving an error (FF-11 posture).
            raise TenantNotActiveError("tenant is not available")

        engine = self._engine_for(record)
        connection = engine.connect()
        try:
            self._assert_identity(connection, record, slug)
        except TenantBindingError:
            connection.invalidate()
            self._quarantine(slug, engine)
            raise
        # The assertion's SELECT opened a read-only transaction; end it so
        # the session below owns its transaction outright — a session
        # joined to an externally-begun transaction cannot truly commit,
        # and its writes would silently vanish on connection close.
        connection.rollback()
        session = Session(bind=connection)
        try:
            yield TenantContext(
                tenant_id=record.tenant_id,
                tenant_slug=record.slug,
                session=session,
            )
        finally:
            session.close()
            connection.close()

    def dispose(self) -> None:
        """Release every pool. App shutdown only."""
        for engine in self._engines.values():
            engine.dispose()
        self._engines.clear()

    # -- internal ------------------------------------------------------------

    def _engine_for(self, record: TenantRecord) -> Engine:
        engine = self._engines.get(record.slug)
        if engine is None:
            # Dev credential model: the base URL's credentials serve every
            # tenant database. The production integration point is here —
            # resolve tenant_databases.credential_ref via the secret store
            # and build a per-tenant URL with per-tenant credentials, so a
            # compromised registry yields the map, not the territory (T-20).
            url = with_database(sqlalchemy_url(self._base_url), record.database_name)
            engine = create_engine(
                url, pool_size=self._pool_size, max_overflow=self._max_overflow
            )
            self._engines[record.slug] = engine
        return engine

    @staticmethod
    def _assert_identity(connection, record: TenantRecord, slug: str) -> None:
        """ARCHITECTURE.md 8.9.1 step 7 — before any other statement."""
        row = connection.execute(
            text("SELECT tenant_id, tenant_slug FROM tenant_identity")
        ).one_or_none()
        if (
            row is None
            or row.tenant_slug != slug
            or row.tenant_id != record.tenant_id
        ):
            raise TenantBindingError("tenant identity assertion failed")

    def _quarantine(self, slug: str, engine: Engine) -> None:
        """A connection answered for the wrong tenant: drop the whole pool,
        forget the engine, drop the registry cache entry, and say so loudly.
        Every connection in that pool is now suspect."""
        log_event(
            _log,
            "tenancy.identity_mismatch",
            level=logging.CRITICAL,
            channel="security",
            bound_slug=slug,
            action="pool_quarantined",
        )
        engine.dispose()
        self._engines.pop(slug, None)
        self._registry.invalidate(slug)
