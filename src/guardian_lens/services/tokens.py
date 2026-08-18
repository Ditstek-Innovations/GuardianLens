"""Token issuing and verification — TRD 12.2.

Access tokens: 15 minutes, carrying subject, tenant slug, principal type
and role grants with site scopes. Refresh tokens: 7 days, rotating; only
their SHA-256 hash is ever stored (TRD 12.4), and the tenant claim inside
them is what routes a refresh to the right tenant database.

TRD 12.2 specifies RS256 with the private key held in the secret store.
PyJWT's RS256 support requires the `cryptography` package, which is not
installed in this environment, so the MVP signs HS256 with a secret from
GL_JWT_SECRET. This module is the single integration point: moving to
RS256 changes ``_ALGORITHM`` and key loading here and nowhere else.
"""

from __future__ import annotations

import hashlib
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

import jwt

from guardian_lens.core.errors import AuthenticationError
from guardian_lens.core.principal import (
    AgentPrincipal,
    Grant,
    HumanPrincipal,
    Principal,
    Role,
)

__all__ = ["TokenService", "RefreshClaims", "hash_token"]

_ALGORITHM = "HS256"  # RS256 once the signing keypair integration lands.

TYPE_HUMAN = "human"
TYPE_AGENT = "agent"
TYPE_REFRESH = "refresh"


def hash_token(token: str) -> bytes:
    """The stored form of a refresh token. Plaintext never touches a row."""
    return hashlib.sha256(token.encode("ascii")).digest()


@dataclass(frozen=True)
class RefreshClaims:
    user_id: UUID
    tenant_slug: str
    token_id: UUID
    family_id: UUID


class TokenService:
    def __init__(
        self,
        secret: str,
        *,
        access_ttl_seconds: int,
        refresh_ttl_seconds: int,
        agent_ttl_seconds: int,
    ) -> None:
        self._secret = secret
        self._access_ttl = access_ttl_seconds
        self._refresh_ttl = refresh_ttl_seconds
        self._agent_ttl = agent_ttl_seconds

    # -- issue ---------------------------------------------------------------

    def issue_access_token(
        self, user_id: UUID, tenant_slug: str, grants: list[tuple[str, UUID]]
    ) -> str:
        return self._encode(
            {
                "sub": str(user_id),
                "tenant": tenant_slug,
                "type": TYPE_HUMAN,
                "roles": [
                    {"role": role, "site_id": str(site_id)}
                    for role, site_id in grants
                ],
            },
            ttl=self._access_ttl,
        )

    def issue_agent_token(
        self, agent_id: UUID, site_id: UUID, tenant_slug: str
    ) -> str:
        # role: none, explicitly. An agent token can never satisfy a role
        # check because it carries no grants at all (BR-S-02).
        return self._encode(
            {
                "sub": str(agent_id),
                "tenant": tenant_slug,
                "type": TYPE_AGENT,
                "site_id": str(site_id),
                "role": "none",
            },
            ttl=self._agent_ttl,
        )

    def issue_refresh_token(
        self, user_id: UUID, tenant_slug: str, family_id: UUID
    ) -> tuple[str, UUID]:
        """Returns (token, token_id). The caller stores hash_token(token)."""
        token_id = uuid.uuid4()
        token = self._encode(
            {
                "sub": str(user_id),
                "tenant": tenant_slug,
                "type": TYPE_REFRESH,
                "jti": str(token_id),
                "family": str(family_id),
            },
            ttl=self._refresh_ttl,
        )
        return token, token_id

    # -- verify --------------------------------------------------------------

    def verify_principal(self, token: str) -> Principal:
        """Decode a bearer token into a typed principal. The tenant slug in
        the returned principal is the ONLY source of tenant identity for the
        request (ARCHITECTURE.md 8.9.2)."""
        claims = self._decode(token)
        token_type = claims.get("type")
        try:
            if token_type == TYPE_HUMAN:
                return HumanPrincipal(
                    user_id=UUID(claims["sub"]),
                    tenant_slug=claims["tenant"],
                    grants=tuple(
                        Grant(role=Role(g["role"]), site_id=UUID(g["site_id"]))
                        for g in claims.get("roles", [])
                    ),
                )
            if token_type == TYPE_AGENT:
                return AgentPrincipal(
                    agent_id=UUID(claims["sub"]),
                    site_id=UUID(claims["site_id"]),
                    tenant_slug=claims["tenant"],
                )
        except (KeyError, ValueError) as exc:
            raise AuthenticationError("invalid token") from exc
        # A refresh token is not a bearer credential for any API route.
        raise AuthenticationError("invalid token")

    def verify_refresh(self, token: str) -> RefreshClaims:
        claims = self._decode(token)
        if claims.get("type") != TYPE_REFRESH:
            raise AuthenticationError("invalid refresh token")
        try:
            return RefreshClaims(
                user_id=UUID(claims["sub"]),
                tenant_slug=claims["tenant"],
                token_id=UUID(claims["jti"]),
                family_id=UUID(claims["family"]),
            )
        except (KeyError, ValueError) as exc:
            raise AuthenticationError("invalid refresh token") from exc

    # -- internal ------------------------------------------------------------

    def _encode(self, claims: dict[str, Any], *, ttl: int) -> str:
        now = datetime.now(timezone.utc)
        claims = {**claims, "iat": now, "exp": now + timedelta(seconds=ttl)}
        return jwt.encode(claims, self._secret, algorithm=_ALGORITHM)

    def _decode(self, token: str) -> dict[str, Any]:
        try:
            return jwt.decode(token, self._secret, algorithms=[_ALGORITHM])
        except jwt.PyJWTError as exc:
            # One generic message for expired/garbled/forged: token failure
            # details help an attacker more than a client.
            raise AuthenticationError("invalid or expired token") from exc
