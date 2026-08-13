"""Authenticated principals and the RBAC capability map — TRD 12.3.

Two principal kinds, two types, on purpose. A single class with an
``is_agent`` flag invites exactly the confusion BR-S-02 exists to prevent:
an agent that accidentally satisfies a human role check. Here an
AgentPrincipal has no ``grants`` attribute at all — the reviewer capability
is not falsy on an agent, it is unrepresentable, mirroring how the schema
gives agents no path into user_roles (DATABASE.md 5.8).

Tenant identity lives on the principal because it comes from the verified
token claim and nowhere else — never from a header, path or body parameter
(ARCHITECTURE.md 8.9.2).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from uuid import UUID

__all__ = ["Role", "Grant", "HumanPrincipal", "AgentPrincipal", "Principal"]


class Role(str, Enum):
    REVIEWER = "reviewer"
    SAFETY_MANAGER = "safety_manager"
    SITE_ADMIN = "site_admin"
    AUDITOR = "auditor"


# TRD 12.3, one row per capability. The agent column of that matrix is
# deliberately absent: an AgentPrincipal never reaches these checks.
DECIDE_ROLES = frozenset({Role.REVIEWER, Role.SAFETY_MANAGER, Role.SITE_ADMIN})
QUEUE_READ_ROLES = frozenset(
    {Role.REVIEWER, Role.SAFETY_MANAGER, Role.SITE_ADMIN, Role.AUDITOR}
)
ZONE_RULE_CONFIG_ROLES = frozenset({Role.SAFETY_MANAGER, Role.SITE_ADMIN})
SITE_CAMERA_CONFIG_ROLES = frozenset({Role.SITE_ADMIN})
AUDIT_READ_ROLES = frozenset({Role.SAFETY_MANAGER, Role.SITE_ADMIN, Role.AUDITOR})


@dataclass(frozen=True, slots=True)
class Grant:
    """One row of user_roles: a role held at one site. Cross-site principals
    hold multiple grants, one per site (AMD-DB-13 — never a null site)."""

    role: Role
    site_id: UUID


@dataclass(frozen=True, slots=True)
class HumanPrincipal:
    user_id: UUID
    tenant_slug: str
    grants: tuple[Grant, ...]

    def site_ids(self, roles: frozenset[Role] | None = None) -> frozenset[UUID]:
        """Sites where this principal holds any of ``roles`` (or any role)."""
        return frozenset(
            g.site_id for g in self.grants if roles is None or g.role in roles
        )

    def holds(self, roles: frozenset[Role]) -> bool:
        return any(g.role in roles for g in self.grants)

    def holds_at_site(self, roles: frozenset[Role], site_id: UUID) -> bool:
        return any(
            g.role in roles and g.site_id == site_id for g in self.grants
        )


@dataclass(frozen=True, slots=True)
class AgentPrincipal:
    """Tenant-bound at registration; carries exactly one site
    (ARCHITECTURE.md 8.9.2). Note: no grants attribute exists."""

    agent_id: UUID
    site_id: UUID
    tenant_slug: str


Principal = HumanPrincipal | AgentPrincipal
