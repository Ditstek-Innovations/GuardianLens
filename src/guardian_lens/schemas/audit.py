"""Audit read schemas — MOD-8."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel


class AuditEntry(BaseModel):
    id: int
    actor_user_id: UUID | None
    actor_agent_id: UUID | None
    action: str
    entity_type: str
    entity_id: UUID | None
    entity_key: str | None
    before_state: dict[str, Any] | None
    after_state: dict[str, Any] | None
    occurred_at: datetime


class AuditPage(BaseModel):
    items: list[AuditEntry]
    next_cursor: str | None
