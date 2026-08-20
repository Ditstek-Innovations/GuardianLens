"""IdentityRepository — users, roles, agents, refresh tokens.

Credential verification happens INSIDE the tenant database
(DATABASE.md 1.5): this repository returns hashes for the identity service
to verify, and stores refresh-token hashes only — never token plaintext
(TRD 12.4).
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime, timedelta, timezone
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.orm import Session

from guardian_lens.repositories.tables import (
    agents,
    password_reset_tokens,
    refresh_tokens,
    roles,
    user_roles,
    users,
)

__all__ = ["IdentityRepository"]


class IdentityRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    # -- users ---------------------------------------------------------------

    def user_by_email(self, email: str) -> sa.Row | None:
        # email is CITEXT; the database does the case-insensitive match.
        return self._session.execute(
            sa.select(users).where(users.c.email == email.strip())
        ).one_or_none()

    def user_by_id(self, user_id: UUID) -> sa.Row | None:
        return self._session.execute(
            sa.select(users).where(users.c.id == user_id)
        ).one_or_none()

    def insert_user(
        self,
        *,
        user_id: UUID,
        email: str,
        full_name: str,
        password_hash: str,
    ) -> None:
        """One user row, active, with NO role grants — signing up creates
        an identity, never access (CS-AU-10). is_active and timestamps come
        from the schema defaults."""
        self._session.execute(
            sa.insert(users).values(
                id=user_id,
                email=email.strip(),
                full_name=full_name,
                password_hash=password_hash,
            )
        )

    def set_user_password(self, user_id: UUID, password_hash: str) -> None:
        self._session.execute(
            sa.update(users)
            .where(users.c.id == user_id)
            .values(password_hash=password_hash, updated_at=sa.func.now())
        )

    def grants_for_user(self, user_id: UUID) -> Sequence[sa.Row]:
        """(role name, site_id) pairs — the token's scope claims."""
        return self._session.execute(
            sa.select(roles.c.name, user_roles.c.site_id)
            .select_from(
                user_roles.join(roles, user_roles.c.role_id == roles.c.id)
            )
            .where(user_roles.c.user_id == user_id)
        ).all()

    def grant_role(
        self,
        *,
        user_id: UUID,
        role_name: str,
        site_id: UUID,
        granted_by: UUID | None,
    ) -> None:
        """Insert one user_roles row. Roles are seeded per tenant; the name
        is resolved in-database so an unknown role fails loudly."""
        role_id = self._session.execute(
            sa.select(roles.c.id).where(roles.c.name == role_name)
        ).scalar_one()
        self._session.execute(
            sa.insert(user_roles).values(
                user_id=user_id,
                role_id=role_id,
                site_id=site_id,
                granted_by=granted_by,
            )
        )

    # -- agents --------------------------------------------------------------

    def agent_by_id(self, agent_id: UUID) -> sa.Row | None:
        return self._session.execute(
            sa.select(agents).where(agents.c.id == agent_id)
        ).one_or_none()

    def record_agent_health(
        self,
        agent_id: UUID,
        *,
        clock_skew_ms: int,
        applied_config_version: int | None,
        agent_version: str | None,
        review_block: list[dict] | None = None,
    ) -> bool:
        """Apply one health beat. last_health_at drives agent_down gap
        inference; applied_config_version is ADR-008's reported fact —
        the version the agent is ACTUALLY running."""
        values: dict[str, object] = {
            "last_health_at": sa.func.now(),
            "last_seen_at": sa.func.now(),
            "clock_skew_ms": clock_skew_ms,
            "status": "active",
        }
        if applied_config_version is not None:
            values["applied_config_version"] = applied_config_version
        if agent_version is not None:
            values["agent_version"] = agent_version
        if review_block is not None:
            values["review_block"] = review_block
        result = self._session.execute(
            sa.update(agents).where(agents.c.id == agent_id).values(**values)
        )
        return result.rowcount == 1

    # -- refresh tokens (migration 0010) -------------------------------------

    def insert_refresh_token(
        self,
        *,
        token_id: UUID,
        user_id: UUID,
        family_id: UUID,
        token_hash: bytes,
        ttl_seconds: int,
    ) -> None:
        self._session.execute(
            sa.insert(refresh_tokens).values(
                id=token_id,
                user_id=user_id,
                family_id=family_id,
                token_hash=token_hash,
                expires_at=datetime.now(timezone.utc)
                + timedelta(seconds=ttl_seconds),
            )
        )

    def refresh_token_by_hash(self, token_hash: bytes) -> sa.Row | None:
        return self._session.execute(
            sa.select(refresh_tokens).where(
                refresh_tokens.c.token_hash == token_hash
            )
        ).one_or_none()

    def revoke_refresh_token(
        self, token_id: UUID, replaced_by: UUID | None = None
    ) -> None:
        self._session.execute(
            sa.update(refresh_tokens)
            .where(refresh_tokens.c.id == token_id)
            .values(revoked_at=sa.func.now(), replaced_by=replaced_by)
        )

    def revoke_token_family(self, family_id: UUID) -> None:
        """Reuse of a revoked token invalidates the WHOLE family — the
        rotation-theft response of TRD 12.2."""
        self._session.execute(
            sa.update(refresh_tokens)
            .where(
                refresh_tokens.c.family_id == family_id,
                refresh_tokens.c.revoked_at.is_(None),
            )
            .values(revoked_at=sa.func.now())
        )

    def revoke_all_refresh_tokens_for_user(self, user_id: UUID) -> None:
        """Revoke every open token in every family — the 0010 revocation
        mechanics applied user-wide. A password reset invalidates every
        session, because the reset exists precisely because the old
        credential can no longer be trusted."""
        self._session.execute(
            sa.update(refresh_tokens)
            .where(
                refresh_tokens.c.user_id == user_id,
                refresh_tokens.c.revoked_at.is_(None),
            )
            .values(revoked_at=sa.func.now())
        )

    # -- password-reset tokens (migration 0011) -------------------------------

    def insert_password_reset_token(
        self,
        *,
        user_id: UUID,
        token_hash: bytes,
        ttl_seconds: int,
    ) -> None:
        self._session.execute(
            sa.insert(password_reset_tokens).values(
                user_id=user_id,
                token_hash=token_hash,
                expires_at=datetime.now(timezone.utc)
                + timedelta(seconds=ttl_seconds),
            )
        )

    def password_reset_token_by_hash(self, token_hash: bytes) -> sa.Row | None:
        return self._session.execute(
            sa.select(password_reset_tokens).where(
                password_reset_tokens.c.token_hash == token_hash
            )
        ).one_or_none()

    def mark_password_reset_token_used(self, token_id: UUID) -> None:
        self._session.execute(
            sa.update(password_reset_tokens)
            .where(password_reset_tokens.c.id == token_id)
            .values(used_at=sa.func.now())
        )

    def invalidate_password_reset_tokens(self, user_id: UUID) -> None:
        """Stamp used_at on every live token so a fresh request leaves at
        most one token per user able to redeem."""
        self._session.execute(
            sa.update(password_reset_tokens)
            .where(
                password_reset_tokens.c.user_id == user_id,
                password_reset_tokens.c.used_at.is_(None),
            )
            .values(used_at=sa.func.now())
        )
