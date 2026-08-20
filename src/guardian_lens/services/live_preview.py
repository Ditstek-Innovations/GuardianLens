"""Process-local latest-frame store for authenticated near-live previews.

The edge remains the only RTSP consumer. It relays a throttled JPEG here;
humans read only the latest frame and never receive camera credentials.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from threading import Lock
from uuid import UUID

__all__ = ["LivePreview", "LivePreviewStore"]


@dataclass(frozen=True, slots=True)
class LivePreview:
    content: bytes
    captured_at: datetime


class LivePreviewStore:
    """Thread-safe latest-value store; a new frame replaces the old one."""

    def __init__(self) -> None:
        self._frames: dict[tuple[str, UUID], LivePreview] = {}
        self._lock = Lock()

    def put(
        self,
        tenant_slug: str,
        camera_id: UUID,
        content: bytes,
        captured_at: datetime,
    ) -> None:
        with self._lock:
            self._frames[(tenant_slug, camera_id)] = LivePreview(
                content=content,
                captured_at=captured_at,
            )

    def get(self, tenant_slug: str, camera_id: UUID) -> LivePreview | None:
        with self._lock:
            return self._frames.get((tenant_slug, camera_id))
