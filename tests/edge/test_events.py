"""Event builder — TRD 10.3 payload discipline and the in-code JPEG."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest

from guardian_lens_edge.events import EventBuilder, iso_utc, placeholder_jpeg
from guardian_lens_edge.rules import CandidateDecision
from guardian_lens_edge.store import EdgeStore
from guardian_lens_edge.uuid7 import uuid7_unix_ms

from tests.edge.conftest import AGENT_ID, CAMERA_ID, at, make_config, make_frame

import uuid


def make_candidate(seconds: float = 5.0) -> CandidateDecision:
    config = make_config()
    return CandidateDecision(
        camera_id=CAMERA_ID,
        zone=config.zones[0],
        rule=config.rules[0],
        confidence=0.75,
        occurred_at=at(seconds),
        frame=make_frame(seconds),
    )


def test_placeholder_jpeg_is_structurally_valid() -> None:
    data = placeholder_jpeg()
    assert data.startswith(b"\xff\xd8")  # SOI
    assert data.endswith(b"\xff\xd9")  # EOI
    assert b"JFIF" in data
    assert len(data) < 512  # tiny, as promised


def test_iso_utc_formats_with_z_suffix() -> None:
    assert iso_utc(at(0)) == "2026-08-12T09:00:00Z"


def test_iso_utc_rejects_naive_datetimes() -> None:
    with pytest.raises(ValueError):
        iso_utc(datetime(2026, 8, 12, 9, 0, 0))


def test_iso_utc_converts_other_zones_to_utc() -> None:
    from datetime import timedelta, timezone as tz

    ist = tz(timedelta(hours=5, minutes=30))
    local = datetime(2026, 8, 12, 14, 30, 0, tzinfo=ist)
    assert iso_utc(local) == "2026-08-12T09:00:00Z"


def test_builder_payload_shape(store: EdgeStore, tmp_path: Path) -> None:
    builder = EventBuilder(store, tmp_path / "spool", AGENT_ID)
    candidate = make_candidate()
    event_id = builder.build_and_enqueue(
        candidate, model_version="synthetic-0.0.0", frame_bytes=None
    )
    row = store.claim_batch(1, now="x")[0]
    payload = row.payload
    assert payload["event_id"] == event_id
    assert set(payload) == {
        "event_id", "camera_id", "zone_id", "rule_id", "rule_snapshot",
        "source", "model_version", "confidence", "occurred_at", "evidence",
    }
    # The verification gate, layer 1: the edge never expresses a status.
    assert "status" not in payload
    assert "reviewer_id" not in payload
    assert "decided_at" not in payload
    assert payload["source"] == "guardian_lens"
    assert payload["model_version"] == "synthetic-0.0.0"
    assert payload["occurred_at"] == "2026-08-12T09:00:05Z"
    # The FULL rule as configured, snapshotted at detection time.
    assert payload["rule_snapshot"] == candidate.rule.model_dump()
    assert payload["rule_snapshot"]["human_readable"] == (
        "Helmet required in Bay 3"
    )
    # data_b64 is added at send time, not stored twice.
    assert payload["evidence"] == {
        "content_type": "image/jpeg",
        "blurred": False,
    }


def test_builder_event_id_is_uuid7_stamped_from_occurred_at(
    store: EdgeStore, tmp_path: Path
) -> None:
    builder = EventBuilder(store, tmp_path / "spool", AGENT_ID)
    candidate = make_candidate(seconds=5.0)
    event_id = uuid.UUID(builder.build_and_enqueue(
        candidate, model_version=None, frame_bytes=None
    ))
    assert event_id.version == 7
    expected_ms = int(candidate.occurred_at.timestamp() * 1000)
    assert uuid7_unix_ms(event_id) == expected_ms


def test_builder_spools_frame_bytes_or_placeholder(
    store: EdgeStore, tmp_path: Path
) -> None:
    builder = EventBuilder(store, tmp_path / "spool", AGENT_ID)
    real_bytes = b"\xff\xd8real-frame\xff\xd9"
    event_id = builder.build_and_enqueue(
        make_candidate(1.0), model_version="m", frame_bytes=real_bytes
    )
    assert (tmp_path / "spool" / f"{event_id}.jpg").read_bytes() == real_bytes

    placeholder_id = builder.build_and_enqueue(
        make_candidate(2.0), model_version="m", frame_bytes=None
    )
    spooled = (tmp_path / "spool" / f"{placeholder_id}.jpg").read_bytes()
    assert spooled == placeholder_jpeg()


def test_builder_enqueues_with_event_id_as_idempotency_key(
    store: EdgeStore, tmp_path: Path
) -> None:
    builder = EventBuilder(store, tmp_path / "spool", AGENT_ID)
    event_id = builder.build_and_enqueue(
        make_candidate(), model_version="m", frame_bytes=None
    )
    row = store.claim_batch(1, now="x")[0]
    assert row.idempotency_key == event_id
    assert row.kind == "event"
    assert row.evidence_path is not None
    assert Path(row.evidence_path).exists()
