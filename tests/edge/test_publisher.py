"""Publisher — IF-E5 delivery semantics against a scripted control plane."""

from __future__ import annotations

from datetime import timedelta
from pathlib import Path

import httpx

from guardian_lens_edge.auth import AgentAuthenticator
from guardian_lens_edge.publisher import Publisher
from guardian_lens_edge.store import EdgeStore

from tests.edge.conftest import FakeControlPlane, at

API = "http://control-plane.test"
NOW = at(0)


def make_publisher(
    store: EdgeStore, plane: FakeControlPlane, **kwargs
) -> Publisher:
    client = plane.client()
    auth = AgentAuthenticator(client, API, "site:agent:secret")
    return Publisher(store, client, API, auth, **kwargs)


def enqueue_event(store: EdgeStore, key: str, tmp_path: Path,
                  with_evidence: bool = True) -> None:
    evidence_path = None
    if with_evidence:
        evidence = tmp_path / f"{key}.jpg"
        evidence.write_bytes(b"\xff\xd8fake\xff\xd9")
        evidence_path = str(evidence)
    store.enqueue_event(
        {"event_id": key, "evidence": {"content_type": "image/jpeg"}},
        evidence_path,
        key,
        created_at=NOW.isoformat(),
    )


def test_201_publishes_and_reclaims(store: EdgeStore, tmp_path: Path) -> None:
    plane = FakeControlPlane()
    publisher = make_publisher(store, plane)
    enqueue_event(store, "e-1", tmp_path)
    report = publisher.tick(NOW)
    assert report.published == 1
    assert store.pending_count() == 0
    assert store.parked_rows() == []
    assert not (tmp_path / "e-1.jpg").exists()
    sent = plane.received_events[0]
    assert sent["event_id"] == "e-1"
    assert sent["evidence"]["data_b64"]  # embedded at send time
    assert "status" not in sent


def test_200_duplicate_is_success(store: EdgeStore, tmp_path: Path) -> None:
    plane = FakeControlPlane()
    plane.event_responses = [200]
    publisher = make_publisher(store, plane)
    enqueue_event(store, "e-1", tmp_path)
    report = publisher.tick(NOW)
    assert report.published == 1
    assert report.parked == 0
    assert store.pending_count() == 0


def test_5xx_retries_with_attempts_and_backoff(
    store: EdgeStore, tmp_path: Path
) -> None:
    plane = FakeControlPlane()
    plane.event_responses = [503, 503]
    publisher = make_publisher(store, plane)
    enqueue_event(store, "e-1", tmp_path)

    report = publisher.tick(NOW)
    assert report.retried == 1
    assert publisher.next_attempt_at == NOW + timedelta(seconds=1)

    # Before the backoff expires nothing is sent at all.
    requests_so_far = len(plane.request_log)
    assert publisher.tick(NOW + timedelta(seconds=0.5)).retried == 0
    assert len(plane.request_log) == requests_so_far

    second_now = NOW + timedelta(seconds=1)
    report = publisher.tick(second_now)
    assert report.retried == 1
    # attempts=1 before this failure -> delay doubles to 2s.
    assert publisher.next_attempt_at == second_now + timedelta(seconds=2)

    # Third attempt succeeds and the row is reclaimed.
    report = publisher.tick(second_now + timedelta(seconds=2))
    assert report.published == 1
    assert store.pending_count() == 0


def test_backoff_caps_at_60_seconds(store: EdgeStore, tmp_path: Path) -> None:
    plane = FakeControlPlane()
    plane.event_responses = [500] * 10
    publisher = make_publisher(store, plane)
    enqueue_event(store, "e-1", tmp_path)
    now = NOW
    delays: list[float] = []
    for _ in range(10):
        publisher.tick(now)
        next_at = publisher.next_attempt_at
        assert next_at is not None
        delays.append((next_at - now).total_seconds())
        now = next_at
    # 1s, 2s, 4s ... capped at 60s, unlimited retries (TRD 5.6).
    assert delays == [1, 2, 4, 8, 16, 32, 60, 60, 60, 60]


def test_408_is_retryable(store: EdgeStore, tmp_path: Path) -> None:
    plane = FakeControlPlane()
    plane.event_responses = [408]
    publisher = make_publisher(store, plane)
    enqueue_event(store, "e-1", tmp_path)
    assert publisher.tick(NOW).retried == 1
    assert store.pending_count() == 1


def test_network_error_is_retryable(store: EdgeStore, tmp_path: Path) -> None:
    plane = FakeControlPlane()
    plane.event_responses = [httpx.ConnectError("boom")]
    publisher = make_publisher(store, plane)
    enqueue_event(store, "e-1", tmp_path)
    report = publisher.tick(NOW)
    assert report.retried == 1
    assert store.pending_count() == 1
    row = store.claim_batch(1, now=NOW.isoformat())[0]
    assert "ConnectError" in (row.last_error or "")


def test_422_parks_with_error_log(
    store: EdgeStore, tmp_path: Path, caplog
) -> None:
    plane = FakeControlPlane()
    plane.event_responses = [422]
    publisher = make_publisher(store, plane)
    enqueue_event(store, "e-1", tmp_path)
    with caplog.at_level("ERROR"):
        report = publisher.tick(NOW)
    assert report.parked == 1
    assert len(store.parked_rows()) == 1
    assert any("422" in record.message for record in caplog.records)
    # Parked rows are never retried.
    assert publisher.tick(NOW + timedelta(seconds=120)).published == 0
    assert len(store.parked_rows()) == 1


def test_other_4xx_parks(store: EdgeStore, tmp_path: Path) -> None:
    plane = FakeControlPlane()
    plane.event_responses = [400]
    publisher = make_publisher(store, plane)
    enqueue_event(store, "e-1", tmp_path)
    assert publisher.tick(NOW).parked == 1


def test_401_reauthenticates_once_then_succeeds(
    store: EdgeStore, tmp_path: Path
) -> None:
    plane = FakeControlPlane()
    plane.event_responses = [401, 201]
    publisher = make_publisher(store, plane)
    enqueue_event(store, "e-1", tmp_path)
    report = publisher.tick(NOW)
    assert report.published == 1
    # One initial token fetch + one re-authentication after the 401.
    assert plane.auth_calls == 2


def test_401_after_reauth_is_retried_not_parked(
    store: EdgeStore, tmp_path: Path
) -> None:
    plane = FakeControlPlane()
    plane.event_responses = [401, 401]
    publisher = make_publisher(store, plane)
    enqueue_event(store, "e-1", tmp_path)
    report = publisher.tick(NOW)
    assert report.retried == 1
    assert report.parked == 0
    assert store.pending_count() == 1


def test_batch_drains_oldest_first(store: EdgeStore, tmp_path: Path) -> None:
    plane = FakeControlPlane()
    publisher = make_publisher(store, plane)
    for index in range(3):
        enqueue_event(store, f"e-{index}", tmp_path)
    store.enqueue_gap({"gap_id": "g-1"}, "g-1", created_at=NOW.isoformat())
    report = publisher.tick(NOW)
    assert report.published == 4
    assert [event["event_id"] for event in plane.received_events] == [
        "e-0", "e-1", "e-2",
    ]
    # The gap went to its own route, after the earlier events.
    assert plane.request_log[-1] == ("POST", "/api/v1/coverage-gaps")


def test_failure_mid_batch_releases_the_rest_unattempted(
    store: EdgeStore, tmp_path: Path
) -> None:
    plane = FakeControlPlane()
    plane.event_responses = [201, 503]
    publisher = make_publisher(store, plane)
    for index in range(3):
        enqueue_event(store, f"e-{index}", tmp_path)
    report = publisher.tick(NOW)
    assert report.published == 1
    assert report.retried == 1
    assert report.released == 1
    rows = store.claim_batch(10, now=NOW.isoformat())
    attempts = {row.idempotency_key: row.attempts for row in rows}
    assert attempts == {"e-1": 1, "e-2": 0}


def test_missing_evidence_file_parks(store: EdgeStore, tmp_path: Path) -> None:
    plane = FakeControlPlane()
    publisher = make_publisher(store, plane)
    store.enqueue_event(
        {"event_id": "e-1", "evidence": {}},
        str(tmp_path / "vanished.jpg"),
        "e-1",
        created_at=NOW.isoformat(),
    )
    report = publisher.tick(NOW)
    assert report.parked == 1
    assert "evidence" in (store.parked_rows()[0].last_error or "")


def test_gap_and_health_use_their_routes(store: EdgeStore) -> None:
    plane = FakeControlPlane()
    publisher = make_publisher(store, plane)
    store.enqueue_gap({"gap_id": "g-1"}, "g-1", created_at=NOW.isoformat())
    store.enqueue_health({"state": "healthy"}, "h-1",
                         created_at=NOW.isoformat())
    assert publisher.tick(NOW).published == 2
    assert plane.received_gaps == [{"gap_id": "g-1"}]
    assert plane.received_health == [{"state": "healthy"}]
