"""Short-lived PTZ command relay between humans and the site edge agent."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from threading import Lock
from uuid import UUID, uuid4

__all__ = ["PtzCommand", "PtzCommandStore"]


@dataclass(frozen=True, slots=True)
class PtzCommand:
    id: UUID
    camera_id: UUID
    direction: str
    created_at: datetime


class PtzCommandStore:
    """Process-local bounded queue; commands expire instead of moving late."""

    def __init__(self, *, maximum_age_seconds: float = 10.0) -> None:
        self._commands: dict[tuple[str, UUID], list[PtzCommand]] = {}
        self._maximum_age = timedelta(seconds=maximum_age_seconds)
        self._lock = Lock()

    def enqueue(self, tenant_slug: str, site_id: UUID, camera_id: UUID, direction: str) -> PtzCommand:
        command = PtzCommand(uuid4(), camera_id, direction, datetime.now(UTC))
        key = (tenant_slug, site_id)
        with self._lock:
            queue = self._commands.setdefault(key, [])
            queue.append(command)
            # A user cannot build an unbounded movement backlog by clicking.
            del queue[:-20]
        return command

    def take(self, tenant_slug: str, site_id: UUID) -> list[PtzCommand]:
        key = (tenant_slug, site_id)
        now = datetime.now(UTC)
        with self._lock:
            queued = self._commands.pop(key, [])
        return [item for item in queued if now - item.created_at <= self._maximum_age]
