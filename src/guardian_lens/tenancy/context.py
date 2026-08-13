"""The bound tenant context handed to services.

Explicit, immutable, and only constructible by the router after the
tenant_identity assertion has passed. Holding one is the proof that the
session inside it points at the database it claims to
(BACKEND_CODING_RULES 6.1).
"""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy.orm import Session


@dataclass(frozen=True)
class TenantContext:
    """One request, one tenant, one asserted session."""

    tenant_id: UUID
    tenant_slug: str
    session: Session
