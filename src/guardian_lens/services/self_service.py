"""SelfServiceAuthService — sign-up and password reset, CS-AU-10 (v1.4).

Both flows are enumeration-safe BY CONSTRUCTION, not by care: the sign-up
and reset-request methods return None on every path, so the routes have
nothing to vary their response with (CS-AU-16, CS-AU-17). Whether a user,
a site code or an address exists is decided in here and dies in here.

Sign-up grants an identity, never access: the created user holds no role
grants, and the repository scope filters already deny everything to a
grantless user — a site_admin assigns roles later (TRD 12.3). Reset
follows login's tenant-binding shape: the address resolves the tenant
through the user_directory hash map, and every credential fact is checked
INSIDE that tenant's database (DATABASE.md 1.5).

Cost symmetry: each flow spends its Argon2 work BEFORE deciding anything,
so the created/refused paths are not distinguishable by response time —
the same posture as login's dummy verification.
"""

from __future__ import annotations

import logging
import secrets
import uuid
from datetime import datetime, timezone

from argon2 import PasswordHasher
from sqlalchemy.exc import IntegrityError

from guardian_lens.core.errors import InvalidResetTokenError, TenantNotActiveError
from guardian_lens.core.logging import get_logger, log_event
from guardian_lens.core.settings import Settings
from guardian_lens.repositories.audit import AuditRepository
from guardian_lens.repositories.identity import IdentityRepository
from guardian_lens.services.audit import AuditService
from guardian_lens.services.tokens import hash_token
from guardian_lens.tenancy.registry import TenantRegistry
from guardian_lens.tenancy.router import TenantRouter

__all__ = ["SelfServiceAuthService", "RESET_TOKEN_TTL_SECONDS"]

_log = get_logger("guardian_lens.self_service")

# DELIVERY CHANNEL, dev only. This logger is the stand-in for the outbound
# mail integration — see request_password_reset.
_delivery_log = get_logger("guardian_lens.reset_delivery")

_hasher = PasswordHasher()

#: The reset link is a 30-minute, single-use capability.
RESET_TOKEN_TTL_SECONDS = 30 * 60


class SelfServiceAuthService:
    def __init__(
        self,
        registry: TenantRegistry,
        router: TenantRouter,
        settings: Settings,
    ) -> None:
        self._registry = registry
        self._router = router
        self._settings = settings

    # -- sign-up --------------------------------------------------------------

    def sign_up(
        self, *, full_name: str, email: str, password: str, site_code: str
    ) -> None:
        """Create identity-without-access, or silently create nothing.

        Creation requires ALL of: the deployment gate open, the site code
        naming an active tenant, and the address not already claimed in the
        directory. Which condition failed is deliberately not expressible
        in the return type (CS-AU-16).
        """
        # Spend the hash first so every refusal path costs what creation
        # costs. The hash is also the only form the password survives in.
        password_hash = _hasher.hash(password)

        if not self._settings.signup_enabled:
            return
        record = self._registry.get(site_code)
        if record is None or not record.is_active:
            return
        if self._registry.directory_has_email(email):
            return

        user_id = uuid.uuid4()
        try:
            with self._router.bind(record.slug) as ctx:
                repo = IdentityRepository(ctx.session)
                repo.insert_user(
                    user_id=user_id,
                    email=email,
                    full_name=full_name,
                    password_hash=password_hash,
                )
                # Actor-less: nobody authenticated performed this, and
                # chk_audit_has_actor admits an actor-less entry only under
                # a system.* action. The user id rides in entity_id; the
                # state carries the allowlisted user fields and NEVER the
                # password hash (DATABASE.md 10.4).
                AuditService(AuditRepository(ctx.session)).write(
                    action="system.user.signed_up",
                    entity_type="user",
                    entity_id=user_id,
                    after_state={
                        "email": email.strip(),
                        "full_name": full_name,
                        "is_active": True,
                    },
                )
                ctx.session.commit()
                tenant_id = ctx.tenant_id
        except TenantNotActiveError:
            # The tenant fell out of 'active' between the registry check
            # and the bind. Nothing was created; the answer does not change.
            return
        except IntegrityError:
            # uq_users_email: the address exists in the tenant but not in
            # the directory (a half-finished bootstrap). Nothing to create,
            # and nothing a caller may learn from it.
            log_event(
                _log,
                "auth.signup_conflict",
                level=logging.WARNING,
                tenant=record.slug,
            )
            return

        # Tenant row first, directory second — bootstrap's ordering, for
        # bootstrap's reason: a directory entry pointing at a user that
        # does not exist would break login, while a user without a
        # directory entry is invisible and repairable.
        self._registry.register_login_email(email, tenant_id)
        log_event(
            _log,
            "auth.user_signed_up",
            tenant=record.slug,
            user_id=str(user_id),
        )

    # -- password reset -------------------------------------------------------

    def request_password_reset(self, email: str) -> None:
        """Issue a fresh single-use token, or silently issue nothing.

        A fresh request supersedes every live token for the user, so at
        most one token can ever redeem (CS-AU-17)."""
        record = self._registry.resolve_login_email(email)
        if record is None or not record.is_active:
            return

        token = secrets.token_urlsafe(32)
        try:
            with self._router.bind(record.slug) as ctx:
                repo = IdentityRepository(ctx.session)
                user = repo.user_by_email(email)
                if user is None or not user.is_active:
                    return
                repo.invalidate_password_reset_tokens(user.id)
                repo.insert_password_reset_token(
                    user_id=user.id,
                    token_hash=hash_token(token),
                    ttl_seconds=RESET_TOKEN_TTL_SECONDS,
                )
                ctx.session.commit()
        except TenantNotActiveError:
            return

        # SMTP INTEGRATION POINT. There is no mail infrastructure yet, so
        # delivery is this one INFO line on a dedicated logger — the
        # operator's tail of guardian_lens.reset_delivery is the outbox.
        # The mail integration replaces exactly this call and nothing else;
        # the token appears here and in the recipient's link, nowhere else.
        _delivery_log.info("password-reset token for %s: %s", email, token)

    def reset_password(
        self, *, email: str, token: str, new_password: str
    ) -> None:
        """Redeem a token: new credential, token spent, every session dead.

        Every failure — unknown address, foreign token, expired, already
        spent, forged — raises the same InvalidResetTokenError, because
        which one it was is exactly what a probing caller wants to know
        (CS-AU-17)."""
        # Hash first: success and every refusal cost the same Argon2 work.
        new_hash = _hasher.hash(new_password)

        record = self._registry.resolve_login_email(email)
        if record is None or not record.is_active:
            raise InvalidResetTokenError()

        try:
            with self._router.bind(record.slug) as ctx:
                repo = IdentityRepository(ctx.session)
                user = repo.user_by_email(email)
                row = repo.password_reset_token_by_hash(hash_token(token))
                if (
                    user is None
                    or not user.is_active
                    or row is None
                    or row.user_id != user.id
                    or row.used_at is not None
                    or row.expires_at <= datetime.now(timezone.utc)
                ):
                    raise InvalidResetTokenError()

                repo.set_user_password(user.id, new_hash)
                repo.mark_password_reset_token_used(row.id)
                # A reset invalidates every session: the flow exists
                # because the old credential can no longer be trusted, and
                # a live refresh family IS the old credential (TRD 12.2).
                repo.revoke_all_refresh_tokens_for_user(user.id)
                AuditService(AuditRepository(ctx.session)).write(
                    action="system.user.password_reset",
                    entity_type="user",
                    entity_id=user.id,
                )
                ctx.session.commit()
                user_id = user.id
        except TenantNotActiveError:
            raise InvalidResetTokenError() from None

        log_event(
            _log,
            "auth.password_reset_completed",
            channel="security",
            tenant=record.slug,
            user_id=str(user_id),
        )
