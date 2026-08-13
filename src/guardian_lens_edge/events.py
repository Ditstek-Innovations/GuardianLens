"""MOD-4 Event Builder — candidate payload per the TRD 10.3 ingest contract.

The payload deliberately contains NO ``status``, ``reviewer_id`` or
``decided_at`` field: the edge can only produce unverified candidates, the
ingest API rejects those fields with a 400, and the enforcement is layered
precisely so no single component can be refactored into bypassing it
(TRD 5.4). Do not add them here, ever.

``rule_snapshot`` is written HERE, at the edge, at detection time
(ARCHITECTURE.md 6.1 step 6): if the rule is later edited or deleted, the
historical event still shows what actually fired.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from guardian_lens_edge.rules import CandidateDecision
from guardian_lens_edge.store import EdgeStore
from guardian_lens_edge.uuid7 import generate_uuid7

__all__ = ["EventBuilder", "iso_utc", "placeholder_jpeg"]

EVENT_SOURCE_GUARDIAN_LENS = "guardian_lens"


def iso_utc(instant: datetime) -> str:
    """ISO-8601 UTC with Z suffix, as in the TRD 10.3 examples."""
    if instant.tzinfo is None:
        raise ValueError("timestamps must be timezone-aware")
    return (
        instant.astimezone(timezone.utc)
        .isoformat(timespec="seconds")
        .replace("+00:00", "Z")
    )


def placeholder_jpeg() -> bytes:
    """A tiny, structurally valid baseline JPEG (1x1 grey), built in code.

    The synthetic source has no real frame to spool, but the evidence slot
    must still carry a decodable image so the full pipeline — spool file,
    size accounting, base64 embedding, reclaim-on-publish — is exercised for
    real. Generated here so the repository contains no binary fixture.
    """
    parts = [
        b"\xff\xd8",  # SOI
        # APP0 / JFIF
        b"\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00",
        # DQT: table 0, all quantisation steps 16
        b"\xff\xdb\x00\x43\x00" + bytes([16] * 64),
        # SOF0: 8-bit, 1x1, one component (id 1, 1x1 sampling, qtable 0)
        b"\xff\xc0\x00\x0b\x08\x00\x01\x00\x01\x01\x01\x11\x00",
        # DHT DC table 0: a single code, '0', for symbol 0 (category 0)
        b"\xff\xc4\x00\x14\x00\x01" + bytes(15) + b"\x00",
        # DHT AC table 0: a single code, '0', for symbol 0 (EOB)
        b"\xff\xc4\x00\x14\x10\x01" + bytes(15) + b"\x00",
        # SOS: one component, DC/AC table 0; spectral selection 0-63
        b"\xff\xda\x00\x08\x01\x01\x00\x00\x3f\x00",
        # Entropy data: DC category 0 ('0') + EOB ('0'), padded with 1s
        b"\x3f",
        b"\xff\xd9",  # EOI
    ]
    return b"".join(parts)


class EventBuilder:
    """Builds the ingest payload and persists it through IF-E4.

    The evidence frame is written to the local spool and referenced by the
    outbox row; the publisher embeds it as ``data_b64`` at send time so the
    bytes are stored exactly once and row + frame are reclaimed together
    (DATABASE.md 11.3).
    """

    def __init__(self, store: EdgeStore, spool_dir: str | Path,
                 agent_id: str) -> None:
        self._store = store
        self._spool_dir = Path(spool_dir)
        self._spool_dir.mkdir(parents=True, exist_ok=True)
        self._agent_id = agent_id

    def build_and_enqueue(
        self,
        candidate: CandidateDecision,
        *,
        model_version: str | None,
        frame_bytes: bytes | None,
    ) -> str:
        """Persist one candidate; returns the client-generated event_id.

        The UUIDv7 is stamped from ``occurred_at`` — the edge observation
        clock (ADR-007) — so identifier order matches observation order and
        no wall clock is read here.

        ``model_version`` comes from the detector's metadata; it is ``None``
        only for nvr-sourced events (TRD 10.3).
        """
        occurred_ms = int(candidate.occurred_at.timestamp() * 1000)
        event_id = str(generate_uuid7(occurred_ms))
        evidence_path = self._spool_dir / f"{event_id}.jpg"
        evidence_path.write_bytes(
            frame_bytes if frame_bytes is not None else placeholder_jpeg()
        )
        payload = {
            "event_id": event_id,
            "camera_id": candidate.camera_id,
            "zone_id": candidate.zone.zone_id,
            "rule_id": candidate.rule.rule_id,
            # The FULL rule as configured at detection time, not a summary:
            # the reviewer must be able to read exactly what fired (DP-6).
            "rule_snapshot": candidate.rule.model_dump(),
            "source": EVENT_SOURCE_GUARDIAN_LENS,
            "model_version": model_version,
            "confidence": candidate.confidence,
            "occurred_at": iso_utc(candidate.occurred_at),
            # data_b64 is added by the publisher at send time from the
            # spooled file (see class docstring).
            "evidence": {"content_type": "image/jpeg", "blurred": False},
        }
        self._store.enqueue_event(
            payload,
            str(evidence_path),
            idempotency_key=event_id,
            created_at=iso_utc(candidate.occurred_at),
        )
        return event_id
