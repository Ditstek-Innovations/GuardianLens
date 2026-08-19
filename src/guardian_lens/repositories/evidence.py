"""Evidence store — the storage abstraction of DATABASE.md 12.

Key convention (DATABASE.md 12.1), with the tenant prefix in front because
the store serves every tenant from one root at MVP:

    {tenant_slug}/evidence/{site_id}/{yyyy}/{mm}/{dd}/{event_uuid}-{suffix}.jpg

The 128-bit random suffix is a security control, not decoration: without
it, a key derivable from an event UUID the caller already holds turns any
authorisation defect on the evidence route into bulk enumeration of a
site's imagery (threat T-10). Never store evidence under a predictable key.

Objects are immutable: written once, never rewritten. The interface
abstracts filesystem [MVP] vs S3 [V1] (TRD 6.4).
"""

from __future__ import annotations

import logging
import re
import secrets
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from uuid import UUID

__all__ = ["EvidenceStore", "FilesystemEvidenceStore", "make_evidence_key"]

_log = logging.getLogger(__name__)

#: Everything a legal key may contain. Reads validate against this before
#: touching storage, so a tampered evidence_ref cannot traverse paths.
_KEY_PATTERN = re.compile(
    r"^[a-z0-9][a-z0-9_-]*/evidence/[0-9a-f-]{36}/\d{4}/\d{2}/\d{2}/"
    r"[0-9a-f-]{36}-[0-9a-f]{32}\.jpg$"
)


def make_evidence_key(
    tenant_slug: str, site_id: UUID, event_uuid: UUID, received_at: datetime
) -> str:
    suffix = secrets.token_hex(16)  # 128 bits of unguessability
    return (
        f"{tenant_slug}/evidence/{site_id}/"
        f"{received_at:%Y}/{received_at:%m}/{received_at:%d}/"
        f"{event_uuid}-{suffix}.jpg"
    )


class EvidenceStore(ABC):
    """Storage abstraction. Callers hold keys, never paths."""

    @abstractmethod
    def put(self, key: str, content: bytes) -> None:
        """Store an immutable object. A key is written at most once."""

    @abstractmethod
    def get(self, key: str) -> bytes | None:
        """Fetch an object, or None when absent. Possession of a key grants
        nothing — the object-level authorisation check happens in the
        service before this is called (BACKEND_CODING_RULES 20)."""

    @abstractmethod
    def healthy(self) -> bool:
        """Is the store usable? Feeds /health/ready."""


class FilesystemEvidenceStore(EvidenceStore):
    """[MVP] — local filesystem under one root, per TRD 12.4 the at-rest
    protection is volume/filesystem encryption, not application crypto."""

    def __init__(self, root: str | Path) -> None:
        self._root = Path(root)
        self._root.mkdir(parents=True, exist_ok=True)

    def _path(self, key: str) -> Path:
        if not _KEY_PATTERN.fullmatch(key):
            # Fail closed on any key this store did not shape itself.
            raise ValueError("malformed evidence key")
        path = (self._root / key).resolve()
        if not path.is_relative_to(self._root.resolve()):
            raise ValueError("evidence key escapes the store root")
        return path

    def put(self, key: str, content: bytes) -> None:
        path = self._path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists():
            # Immutability: a frame is never re-written (DATABASE.md 12.2).
            raise FileExistsError(f"evidence object already exists: {key}")
        path.write_bytes(content)
        _log.info("evidence stored key=%s bytes=%d", key, len(content))

    def get(self, key: str) -> bytes | None:
        path = self._path(key)
        if not path.is_file():
            return None
        return path.read_bytes()

    def healthy(self) -> bool:
        return self._root.is_dir()
