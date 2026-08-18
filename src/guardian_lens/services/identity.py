"""IdentityService — MOD-12: authenticate, issue tokens, rotate refresh.

Login is the one flow where tenant binding precedes authentication,
because the tenant must be resolved from the submitted address before any
tenant database is opened (DATABASE.md 1.5). The resolution goes through
the user_directory hash map — the address itself is never stored in the
control database — and credential verification happens INSIDE the tenant
database, so C2/C4 data never leaves the tenant boundary.

Unknown address and wrong password return the same error type, the same
shape, and comparable timing: a dummy Argon2 verification runs on the
unknown-address path so the two are not distinguishable by response time.
"""

from __future__ import annotations

import logging
import uuid
from contextlib import ExitStack
from dataclasses import dataclass
from uuid import UUID

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

from guardian_lens.core.errors import (
    AuthenticationError,
    InvalidCredentialsError,
    TenantNotActiveError,
)
from guardian_lens.core.logging import get_logger, log_event
from guardian_lens.repositories.identity import IdentityRepository
from guardian_lens.services.tokens import TokenService, hash_token
from guardian_lens.tenancy.registry import TenantRegistry
from guardian_lens.tenancy.router import TenantRouter

__all__ = ["IdentityService", "TokenPair", "AgentToken"]

_log = get_logger("guardian_lens.identity")

_hasher = PasswordHasher()
# Verified against on the unknown-address path so that path costs the same
# as a real verification (DATABASE.md 1.5 — comparable timing).
_DUMMY_HASH = _hasher.hash("gl-timing-equalisation-dummy")

_INVALID_REFRESH = "invalid refresh token"


@dataclass(frozen=True)
class TokenPair:
    access_token: str
    refresh_token: str
    expires_in: int
    user_id: UUID
    full_name: str
    roles: list[str]


@dataclass(frozen=True)
class AgentToken:
    access_token: str
    expires_in: int


class IdentityService:
    def __init__(
        self,
        registry: TenantRegistry,
        router: TenantRouter,
        tokens: TokenService,
        *,
        access_ttl_seconds: int,
        refresh_ttl_seconds: int,
        agent_ttl_seconds: int,
    ) -> None:
        self._registry = registry
        self._router = router
        self._tokens = tokens
        self._access_ttl = access_ttl_seconds
        self._refresh_ttl = refresh_ttl_seconds
        self._agent_ttl = agent_ttl_seconds

    # -- human login ---------------------------------------------------------

    def login(self, email: str, password: str) -> TokenPair:
        record = self._registry.resolve_login_email(email)
        if record is None or not record.is_active:
            # Same error, same cost, whether the address is unknown or its
            # tenant is unavailable. No user enumeration (TRD 10.2).
            self._burn_verification(password)
            raise InvalidCredentialsError()

        with self._router.bind(record.slug) as ctx:
            repo = IdentityRepository(ctx.session)
            user = repo.user_by_email(email)
            if user is None or not user.is_active or user.password_hash is None:
                self._burn_verification(password)
                raise InvalidCredentialsError()
            try:
                _hasher.verify(user.password_hash, password)
            except VerifyMismatchError:
                raise InvalidCredentialsError() from None

            grants = [(g.name, g.site_id) for g in repo.grants_for_user(user.id)]
            access = self._tokens.issue_access_token(user.id, record.slug, grants)
            family_id = uuid.uuid4()
            refresh, token_id = self._tokens.issue_refresh_token(
                user.id, record.slug, family_id
            )
            repo.insert_refresh_token(
                token_id=token_id,
                user_id=user.id,
                family_id=family_id,
                token_hash=hash_token(refresh),
                ttl_seconds=self._refresh_ttl,
            )
            ctx.session.commit()
            return TokenPair(
                access_token=access,
                refresh_token=refresh,
                expires_in=self._access_ttl,
                user_id=user.id,
                full_name=user.full_name,
                roles=sorted({role for role, _ in grants}),
            )

    def refresh(self, refresh_token: str) -> TokenPair:
        """Rotate: each refresh issues a new token and revokes the prior
        one. Reuse of a revoked token invalidates the whole family and
        raises a security alert (TRD 12.2)."""
        claims = self._tokens.verify_refresh(refresh_token)
        with self._router.bind(claims.tenant_slug) as ctx:
            repo = IdentityRepository(ctx.session)
            row = repo.refresh_token_by_hash(hash_token(refresh_token))
            if row is None:
                raise AuthenticationError(_INVALID_REFRESH)
            if row.revoked_at is not None:
                # Rotation-reuse: someone presented a token that was already
                # rotated away — the family is considered stolen.
                repo.revoke_token_family(row.family_id)
                ctx.session.commit()
                log_event(
                    _log,
                    "auth.refresh_reuse_detected",
                    level=logging.WARNING,
                    channel="security",
                    family_revoked=True,
                )
                raise AuthenticationError(_INVALID_REFRESH)

            user = repo.user_by_id(row.user_id)
            if user is None or not user.is_active:
                raise AuthenticationError(_INVALID_REFRESH)

            grants = [(g.name, g.site_id) for g in repo.grants_for_user(user.id)]
            access = self._tokens.issue_access_token(
                user.id, claims.tenant_slug, grants
            )
            new_refresh, new_id = self._tokens.issue_refresh_token(
                user.id, claims.tenant_slug, row.family_id
            )
            repo.insert_refresh_token(
                token_id=new_id,
                user_id=user.id,
                family_id=row.family_id,
                token_hash=hash_token(new_refresh),
                ttl_seconds=self._refresh_ttl,
            )
            repo.revoke_refresh_token(row.id, replaced_by=new_id)
            ctx.session.commit()
            return TokenPair(
                access_token=access,
                refresh_token=new_refresh,
                expires_in=self._access_ttl,
                user_id=user.id,
                full_name=user.full_name,
                roles=sorted({role for role, _ in grants}),
            )

    def logout(self, refresh_token: str) -> None:
        """Revoke the presented refresh token's family. Idempotent — a
        second logout with the same token is not an error."""
        claims = self._tokens.verify_refresh(refresh_token)
        with self._router.bind(claims.tenant_slug) as ctx:
            repo = IdentityRepository(ctx.session)
            row = repo.refresh_token_by_hash(hash_token(refresh_token))
            if row is not None:
                repo.revoke_token_family(row.family_id)
                ctx.session.commit()

    # -- agent exchange ------------------------------------------------------

    def agent_login(self, credential: str) -> AgentToken:
        """Exchange a long-lived agent credential for a short-lived token.

        Credential format: ``slug:agent_id:secret``. The slug is ROUTING
        ONLY — it selects which tenant database to verify in; the proof is
        the secret, verified against agents.credential_hash in-tenant. An
        agent credential resolves to exactly one tenant and one site
        (ARCHITECTURE.md 8.9.2); a compromised agent cannot address
        another tenant because its secret exists in only one database.
        """
        try:
            slug, agent_id_raw, secret = credential.split(":", 2)
            agent_id = UUID(agent_id_raw)
        except ValueError:
            raise InvalidCredentialsError() from None

        with ExitStack() as stack:
            try:
                ctx = stack.enter_context(self._router.bind(slug))
            except TenantNotActiveError:
                # Same generic failure as a bad secret: whether a slug
                # exists is not information an unauthenticated caller may
                # probe.
                raise InvalidCredentialsError() from None
            repo = IdentityRepository(ctx.session)
            agent = repo.agent_by_id(agent_id)
            if agent is None:
                self._burn_verification(secret)
                raise InvalidCredentialsError()
            try:
                _hasher.verify(agent.credential_hash, secret)
            except VerifyMismatchError:
                raise InvalidCredentialsError() from None
            token = self._tokens.issue_agent_token(
                agent.id, agent.site_id, ctx.tenant_slug
            )
            return AgentToken(access_token=token, expires_in=self._agent_ttl)

    # -- internal ------------------------------------------------------------

    @staticmethod
    def _burn_verification(password: str) -> None:
        """Spend one Argon2 verification so failure paths cost the same
        with and without a matching account."""
        try:
            _hasher.verify(_DUMMY_HASH, password)
        except VerifyMismatchError:
            pass
