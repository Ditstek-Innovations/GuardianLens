"""Edge store — DATABASE.md 11.2 schema, 11.3 state machine, 11.4 levels."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from guardian_lens_edge.store import (
    BackpressureLevel,
    CounterKind,
    EdgeStore,
)

NOW = "2026-08-12T09:00:00+00:00"


def test_pragmas_wal_and_synchronous_full(store: EdgeStore) -> None:
    conn = store._conn  # white-box: the pragmas ARE the spec (11.1)
    assert conn.execute("PRAGMA journal_mode").fetchone()[0] == "wal"
    assert conn.execute("PRAGMA synchronous").fetchone()[0] == 2  # FULL
    assert conn.execute("PRAGMA foreign_keys").fetchone()[0] == 1


def test_schema_tables_exist(store: EdgeStore) -> None:
    names = {
        row[0]
        for row in store._conn.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table'"
        )
    }
    assert {"outbox", "agent_config", "open_gaps", "detection_counters"} <= names


def test_claim_is_oldest_first_and_kind_agnostic(store: EdgeStore) -> None:
    store.enqueue_event({"n": 1}, None, "e-1", created_at=NOW)
    store.enqueue_gap({"n": 2}, "g-1", created_at=NOW)
    store.enqueue_health({"n": 3}, "h-1", created_at=NOW)
    store.enqueue_event({"n": 4}, None, "e-2", created_at=NOW)
    batch = store.claim_batch(10, now=NOW)
    assert [row.payload["n"] for row in batch] == [1, 2, 3, 4]
    assert [row.kind for row in batch] == [
        "event", "coverage_gap", "health", "event",
    ]
    assert all(row.state == "inflight" for row in batch)


def test_claimed_rows_are_not_reclaimed(store: EdgeStore) -> None:
    store.enqueue_event({}, None, "e-1", created_at=NOW)
    assert len(store.claim_batch(10, now=NOW)) == 1
    assert store.claim_batch(10, now=NOW) == []


def test_claim_respects_limit(store: EdgeStore) -> None:
    for index in range(5):
        store.enqueue_event({}, None, f"e-{index}", created_at=NOW)
    assert len(store.claim_batch(2, now=NOW)) == 2
    assert store.pending_count() == 3


def test_mark_retry_returns_to_pending_and_counts_attempt(
    store: EdgeStore,
) -> None:
    store.enqueue_event({}, None, "e-1", created_at=NOW)
    row = store.claim_batch(1, now=NOW)[0]
    store.mark_retry(row.id, "HTTP 503", now=NOW)
    reclaimed = store.claim_batch(1, now=NOW)
    assert len(reclaimed) == 1
    assert reclaimed[0].attempts == 1
    assert reclaimed[0].last_error == "HTTP 503"


def test_release_claim_does_not_count_an_attempt(store: EdgeStore) -> None:
    store.enqueue_event({}, None, "e-1", created_at=NOW)
    row = store.claim_batch(1, now=NOW)[0]
    store.release_claim(row.id)
    reclaimed = store.claim_batch(1, now=NOW)
    assert len(reclaimed) == 1
    assert reclaimed[0].attempts == 0
    assert reclaimed[0].last_error is None


def test_mark_published_reclaims_row_and_evidence(
    store: EdgeStore, tmp_path: Path
) -> None:
    evidence = tmp_path / "frame.jpg"
    evidence.write_bytes(b"\xff\xd8jpeg\xff\xd9")
    store.enqueue_event({}, str(evidence), "e-1", created_at=NOW)
    row = store.claim_batch(1, now=NOW)[0]
    store.mark_published(row.id)
    assert store.pending_count() == 0
    assert store.claim_batch(10, now=NOW) == []
    assert not evidence.exists()


def test_parked_is_terminal_never_reclaimed_never_deleted(
    store: EdgeStore,
) -> None:
    store.enqueue_event({}, None, "poison", created_at=NOW)
    store.enqueue_event({}, None, "good", created_at=NOW)
    first, second = store.claim_batch(2, now=NOW)
    store.park(first.id, "HTTP 422", now=NOW)
    store.mark_retry(second.id, "HTTP 503", now=NOW)
    # The parked row is never claimed again; the retried one is.
    assert [row.idempotency_key for row in store.claim_batch(10, now=NOW)] == [
        "good"
    ]
    parked = store.parked_rows()
    assert len(parked) == 1
    assert parked[0].idempotency_key == "poison"
    assert parked[0].last_error == "HTTP 422"


def test_park_is_alert_logged(store: EdgeStore, caplog) -> None:
    store.enqueue_event({}, None, "poison", created_at=NOW)
    row = store.claim_batch(1, now=NOW)[0]
    with caplog.at_level("ERROR", logger="guardian_lens_edge.store"):
        store.park(row.id, "HTTP 422", now=NOW)
    assert any("parked" in record.message for record in caplog.records)


def test_duplicate_idempotency_key_rejected_per_kind(store: EdgeStore) -> None:
    store.enqueue_event({}, None, "same-key", created_at=NOW)
    with pytest.raises(sqlite3.IntegrityError):
        store.enqueue_event({}, None, "same-key", created_at=NOW)
    # A different kind may reuse the key: uniqueness is (kind, key).
    store.enqueue_gap({}, "same-key", created_at=NOW)


def test_counters_accumulate(store: EdgeStore) -> None:
    bucket = "2026-08-12T09:00:00+00:00"
    for _ in range(3):
        store.increment_counter(bucket, "cam-1", "rule-1",
                                CounterKind.BELOW_THRESHOLD)
    store.increment_counter(bucket, "cam-1", "rule-1",
                            CounterKind.DEBOUNCE_SUPPRESSED)
    store.increment_counter(bucket, "cam-2", "rule-1",
                            CounterKind.OUTSIDE_ZONE)
    rows = {(row["camera_id"]): row for row in store.counters()}
    assert rows["cam-1"]["below_threshold"] == 3
    assert rows["cam-1"]["debounce_suppressed"] == 1
    assert rows["cam-1"]["outside_zone"] == 0
    assert rows["cam-2"]["outside_zone"] == 1


def test_open_gap_survives_restart(tmp_path: Path) -> None:
    db_path = tmp_path / "edge.sqlite3"
    first = EdgeStore(db_path, warning_bytes=1000, critical_bytes=2000)
    first.open_gap("gap-1", "cam-1", "stream_lost", NOW)
    first.close()
    # Simulated restart: a fresh store over the same file.
    second = EdgeStore(db_path, warning_bytes=1000, critical_bytes=2000)
    try:
        gaps = second.open_gaps()
        assert len(gaps) == 1
        assert gaps[0].gap_id == "gap-1"
        assert gaps[0].reason == "stream_lost"
        second.close_gap("gap-1")
        assert second.open_gaps() == []
    finally:
        second.close()


def test_outbox_survives_restart(tmp_path: Path) -> None:
    db_path = tmp_path / "edge.sqlite3"
    first = EdgeStore(db_path, warning_bytes=1000, critical_bytes=2000)
    first.enqueue_event({"n": 1}, None, "e-1", created_at=NOW)
    first.close()
    second = EdgeStore(db_path, warning_bytes=1000, critical_bytes=2000)
    try:
        assert second.pending_count() == 1
    finally:
        second.close()


def test_config_round_trip_and_fetch_error(store: EdgeStore) -> None:
    store.save_config(7, {"config_version": 7, "rules": []}, applied_at=NOW)
    row = store.load_config()
    assert row is not None
    assert row.config_version == 7
    assert row.document["config_version"] == 7
    assert row.last_fetch_error is None
    store.record_fetch_result(fetched_at=NOW, error="HTTP 503")
    row = store.load_config()
    assert row is not None
    assert row.last_fetch_error == "HTTP 503"
    assert row.config_version == 7  # applied document untouched


def test_usage_counts_payload_and_evidence(
    store: EdgeStore, tmp_path: Path
) -> None:
    evidence = tmp_path / "frame.jpg"
    evidence.write_bytes(b"x" * 100)
    store.enqueue_event({"k": "v"}, str(evidence), "e-1", created_at=NOW)
    usage = store.usage_bytes()
    assert usage >= 100
    assert usage == len('{"k":"v"}') + 100


def test_backpressure_levels(tmp_path: Path) -> None:
    edge_store = EdgeStore(
        tmp_path / "edge.sqlite3", warning_bytes=150, critical_bytes=300
    )
    try:
        assert edge_store.backpressure_level() is BackpressureLevel.NORMAL
        evidence = tmp_path / "a.jpg"
        evidence.write_bytes(b"x" * 148)
        edge_store.enqueue_event({}, str(evidence), "e-1", created_at=NOW)
        # 148 + len("{}") = 150 — exactly at the warning threshold.
        assert edge_store.backpressure_level() is BackpressureLevel.WARNING
        evidence_b = tmp_path / "b.jpg"
        evidence_b.write_bytes(b"x" * 148)
        edge_store.enqueue_event({}, str(evidence_b), "e-2", created_at=NOW)
        assert edge_store.backpressure_level() is BackpressureLevel.CRITICAL
    finally:
        edge_store.close()


def test_threshold_parameters_are_validated(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        EdgeStore(tmp_path / "a.db", warning_bytes=0, critical_bytes=10)
    with pytest.raises(ValueError):
        EdgeStore(tmp_path / "b.db", warning_bytes=100, critical_bytes=50)
