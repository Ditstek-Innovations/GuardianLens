"""AuditRepository — insert-only, structurally.

TRD 6.4: no update or delete method is exposed AT ALL. The append-only
guarantee therefore holds twice — once because this interface has no way
to express the operation, and once because the database triggers reject it
regardless of caller. Only the second survives a direct connection, which
is why both exist (ARCHITECTURE.md 5.3).

Do not add an update or delete method to this class. There is no valid
reason, and BACKEND_CODING_RULES 15 prohibits it.
"""

from __future__ import annotations

import ipaddress
from collections.abc import Sequence
from datetime import datetime
from typing import Any
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.orm import Session

from guardian_lens.repositories.tables import audit_log

__all__ = ["AuditRepository"]


def _valid_inet(ip_address_text: str | None) -> str | None:
    """audit_log.ip_address is INET; a non-address (a proxy's label, a test
    client's placeholder) is recorded as absent rather than failing the
    transaction the audit entry shares."""
    if ip_address_text is None:
        return None
    try:
        ipaddress.ip_address(ip_address_text)
    except ValueError:
        return None
    return ip_address_text


class AuditRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def insert(
        self,
        *,
        action: str,
        entity_type: str,
        actor_user_id: UUID | None = None,
        actor_agent_id: UUID | None = None,
        entity_id: UUID | None = None,
        entity_key: str | None = None,
        before_state: dict[str, Any] | None = None,
        after_state: dict[str, Any] | None = None,
        ip_address: str | None = None,
    ) -> None:
        """Append one entry, inside the caller's transaction — the same
        transaction as the mutation it records (BR-AU-03, BR-C-01)."""
        self._session.execute(
            sa.insert(audit_log).values(
                action=action,
                entity_type=entity_type,
                actor_user_id=actor_user_id,
                actor_agent_id=actor_agent_id,
                entity_id=entity_id,
                entity_key=entity_key,
                before_state=before_state,
                after_state=after_state,
                ip_address=_valid_inet(ip_address),
            )
        )

    def page(
        self,
        *,
        limit: int,
        after_id: int | None = None,
        entity_type: str | None = None,
        entity_id: UUID | None = None,
        occurred_from: datetime | None = None,
        occurred_to: datetime | None = None,
    ) -> Sequence[sa.Row]:
        """Read a page, newest first, cursor on the monotonic id — never
        OFFSET (DATABASE.md 7.3)."""
        conditions = []
        if after_id is not None:
            conditions.append(audit_log.c.id < after_id)
        if entity_type is not None:
            conditions.append(audit_log.c.entity_type == entity_type)
        if entity_id is not None:
            conditions.append(audit_log.c.entity_id == entity_id)
        if occurred_from is not None:
            conditions.append(audit_log.c.occurred_at >= occurred_from)
        if occurred_to is not None:
            conditions.append(audit_log.c.occurred_at <= occurred_to)
        return self._session.execute(
            sa.select(audit_log)
            .where(*conditions)
            .order_by(audit_log.c.id.desc())
            .limit(limit)
        ).all()
