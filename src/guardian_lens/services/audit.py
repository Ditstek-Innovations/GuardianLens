"""AuditService — MOD-8. The one writer of tenant audit entries.

Every entry passes AuditWriteGuard's per-entity allowlist before insert,
and the insert happens in the CALLER's transaction: DecisionService and
ConfigurationService call this inside the same transaction as their
mutation, so an audit failure rolls the mutation back (BR-AU-03, BR-C-01
— a change that cannot be audited must not take effect).
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from guardian_lens.guards.audit_write import AuditWriteGuard
from guardian_lens.repositories.audit import AuditRepository

__all__ = ["AuditService"]


class AuditService:
    def __init__(self, repository: AuditRepository) -> None:
        self._repository = repository

    def write(
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
        self._repository.insert(
            action=action,
            entity_type=entity_type,
            actor_user_id=actor_user_id,
            actor_agent_id=actor_agent_id,
            entity_id=entity_id,
            entity_key=entity_key,
            before_state=AuditWriteGuard.filter_state(entity_type, before_state),
            after_state=AuditWriteGuard.filter_state(entity_type, after_state),
            ip_address=ip_address,
        )
