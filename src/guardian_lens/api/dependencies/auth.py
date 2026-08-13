"""Authentication and authorisation dependencies — TRD 12.3 point 1.

Route-level dependency injection asserts the required principal type and
role BEFORE the controller executes. These are the first enforcement
layer; the repository-level scope filters are the second, and the
object-level evidence check is the third.

Principal typing is strict in both directions: an agent token can never
satisfy a human dependency and a human token can never satisfy the agent
dependency — both are 403 (BR-S-02 and its mirror on ingest).
"""

from __future__ import annotations

from fastapi import Depends, Request

from guardian_lens.core.errors import AuthenticationError, PrincipalTypeError
from guardian_lens.core.logging import user_id_var
from guardian_lens.core.principal import (
    AUDIT_READ_ROLES,
    DECIDE_ROLES,
    QUEUE_READ_ROLES,
    SITE_CAMERA_CONFIG_ROLES,
    ZONE_RULE_CONFIG_ROLES,
    AgentPrincipal,
    HumanPrincipal,
    Principal,
    Role,
)
from guardian_lens.services.tokens import TokenService

__all__ = [
    "get_principal",
    "require_human",
    "require_agent",
    "require_decide_role",
    "require_queue_read",
    "require_audit_read",
    "require_site_admin",
    "require_config_role",
]


def get_principal(request: Request) -> Principal:
    """Verify the bearer token and type the principal. The tenant slug in
    the result is the request's ONLY source of tenant identity."""
    header = request.headers.get("Authorization", "")
    scheme, _, token = header.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise AuthenticationError("missing bearer token")
    tokens: TokenService = request.app.state.token_service
    principal = tokens.verify_principal(token.strip())
    if isinstance(principal, HumanPrincipal):
        user_id_var.set(str(principal.user_id))
    return principal


def require_human(
    principal: Principal = Depends(get_principal),
) -> HumanPrincipal:
    if not isinstance(principal, HumanPrincipal):
        # An agent principal on a human route — BR-S-02's API face.
        raise PrincipalTypeError("agent principals cannot access this route")
    return principal


def require_agent(
    principal: Principal = Depends(get_principal),
) -> AgentPrincipal:
    if not isinstance(principal, AgentPrincipal):
        # The mirror rule: a human token can never hit ingest. Keeping the
        # two write paths disjoint is what makes "only MOD-7 transitions an
        # event" checkable.
        raise PrincipalTypeError("this route accepts agent principals only")
    return principal


def _require_role(roles: frozenset[Role], description: str):
    def dependency(
        principal: HumanPrincipal = Depends(require_human),
    ) -> HumanPrincipal:
        if not principal.holds(roles):
            raise PrincipalTypeError(f"requires {description}")
        return principal

    return dependency


# Role gates per the TRD 12.3 matrix. Which SITE a grant applies to is
# checked by the services/repositories against the target object — a role
# held anywhere opens the route, scope decides the rows.
require_decide_role = _require_role(DECIDE_ROLES, "a deciding role")
require_queue_read = _require_role(QUEUE_READ_ROLES, "queue read access")
require_audit_read = _require_role(AUDIT_READ_ROLES, "audit read access")
require_site_admin = _require_role(SITE_CAMERA_CONFIG_ROLES, "site_admin")
require_config_role = _require_role(
    ZONE_RULE_CONFIG_ROLES, "safety_manager or site_admin"
)
