"""Tenant registry — the cached view of the control database.

The control database holds routing, lifecycle and operational state only
(ADR-017). This module reads it and answers exactly two questions:

  * which tenant does this slug / email-hash resolve to, and
  * may it be served right now (status == 'active').

The cache exists because the control database is availability-critical —
if routing is unavailable, every tenant is unavailable — so lookups are
served from cache with a short TTL and explicit invalidation on lifecycle
events (ARCHITECTURE.md 8.9.1 note). A cached entry can therefore be
stale, which is precisely why the router asserts tenant_identity on every
connection acquisition: the cache is an optimisation, the assertion is the
control.
"""

from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from guardian_lens.db.urls import sqlalchemy_url, tenant_database_name

__all__ = ["TenantRecord", "TenantRegistry", "email_hash"]


def email_hash(email: str) -> bytes:
    """sha256(lower(trim(email))) — DATABASE.md 1.5. The address itself is
    never stored in the control database; only this hash routes a login."""
    return hashlib.sha256(email.strip().lower().encode("utf-8")).digest()


@dataclass(frozen=True)
class TenantRecord:
    tenant_id: UUID
    slug: str
    status: str
    # Physical database name. From tenant_databases when registered there;
    # otherwise derived deterministically from the slug — the same derivation
    # provisioning used to create it (db/urls.tenant_database_name).
    database_name: str

    @property
    def is_active(self) -> bool:
        return self.status == "active"


class TenantRegistry:
    """Read-mostly, cached; invalidated on tenant lifecycle events."""

    def __init__(self, control_db_url: str, cache_ttl_seconds: float = 30.0) -> None:
        # The registry owns the only control-plane engine in the API process.
        # Small pool: the control DB is read-mostly and heavily cached.
        self._engine: Engine = create_engine(
            sqlalchemy_url(control_db_url), pool_size=2, max_overflow=2,
            pool_pre_ping=True,
        )
        self._ttl = cache_ttl_seconds
        self._cache: dict[str, tuple[float, TenantRecord | None]] = {}

    # -- cache ---------------------------------------------------------------

    def invalidate(self, slug: str) -> None:
        self._cache.pop(slug, None)

    def invalidate_all(self) -> None:
        self._cache.clear()

    # -- lookups -------------------------------------------------------------

    def get(self, slug: str) -> TenantRecord | None:
        """Resolve a slug to its record, from cache within the TTL."""
        cached = self._cache.get(slug)
        now = time.monotonic()
        if cached is not None and now - cached[0] < self._ttl:
            return cached[1]
        record = self._load(slug)
        self._cache[slug] = (now, record)
        return record

    def resolve_login_email(self, email: str) -> TenantRecord | None:
        """Tenant for a login address, via the user_directory hash map.

        This is the one deliberate cross-tenant surface (DATABASE.md 1.5,
        threat T-19): a login must resolve to a tenant before any tenant
        database is opened. It returns routing only — never credentials.
        """
        with self._engine.connect() as conn:
            row = conn.execute(
                text("SELECT t.slug FROM user_directory d "
                     "JOIN tenants t ON t.id = d.tenant_id "
                     "WHERE d.email_hash = :h"),
                {"h": email_hash(email)},
            ).one_or_none()
        if row is None:
            return None
        return self.get(row.slug)

    def directory_has_email(self, email: str) -> bool:
        """Is this address already routable? Sign-up must refuse a second
        claim on an address — one email hash resolves to exactly one tenant
        (uq via the primary key), and the answer is never surfaced to the
        caller of the API (CS-AU-16)."""
        with self._engine.connect() as conn:
            row = conn.execute(
                text("SELECT 1 FROM user_directory WHERE email_hash = :h"),
                {"h": email_hash(email)},
            ).one_or_none()
        return row is not None

    def register_login_email(self, email: str, tenant_id: UUID) -> None:
        """Insert one login-routing row — the same sha256(lower(trim()))
        discipline as bootstrap; the address itself is never stored.

        ON CONFLICT DO NOTHING: two concurrent sign-ups for one address must
        not turn into an error a caller could observe (CS-AU-16) — the row
        either exists or now exists, and the first claim wins.
        """
        with self._engine.begin() as conn:
            conn.execute(
                text(
                    "INSERT INTO user_directory (email_hash, tenant_id) "
                    "VALUES (:h, :t) ON CONFLICT (email_hash) DO NOTHING"
                ),
                {"h": email_hash(email), "t": tenant_id},
            )

    def health_check(self) -> bool:
        """Is the control database reachable? Used by /health/ready."""
        try:
            with self._engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            return True
        except Exception:  # noqa: BLE001 — translated to a readiness signal
            return False

    # -- internal ------------------------------------------------------------

    def _load(self, slug: str) -> TenantRecord | None:
        with self._engine.connect() as conn:
            row = conn.execute(
                text(
                    "SELECT t.id, t.slug, t.status, d.database_name "
                    "FROM tenants t "
                    "LEFT JOIN tenant_databases d ON d.tenant_id = t.id "
                    "WHERE t.slug = :slug"
                ),
                {"slug": slug},
            ).one_or_none()
        if row is None:
            return None
        # credential_ref is NOT resolved here in dev: the per-tenant database
        # credential comes from the base URL. In production this is the
        # secret-store integration point — resolve tenant_databases.
        # credential_ref against the secret manager and never hold the
        # credential in this record (threat T-20).
        return TenantRecord(
            tenant_id=row.id,
            slug=row.slug,
            status=row.status,
            database_name=row.database_name or tenant_database_name(row.slug),
        )
