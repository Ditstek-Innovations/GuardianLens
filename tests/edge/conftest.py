"""Fixtures for the edge agent suite.

Everything runs against a tmp-dir SQLite store and httpx.MockTransport —
no PostgreSQL, no network, no ML dependency. This is deliberate: the edge
agent's rules (D1, the outbox state machine, ADR-008/009) are all
self-contained, and TRD 13.2 says the MVP tests the workflow, not the
detector.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Iterator

import pytest

from guardian_lens_edge.config import (
    AgentConfig,
    CameraConfig,
    RuleConfig,
    ZoneConfig,
)
from guardian_lens_edge.frames import Frame
from guardian_lens_edge.store import EdgeStore

T0 = datetime(2026, 8, 12, 9, 0, 0, tzinfo=timezone.utc)

CAMERA_ID = "11111111-1111-1111-1111-111111111111"
ZONE_ID = "22222222-2222-2222-2222-222222222222"
RULE_ID = "33333333-3333-3333-3333-333333333333"
SITE_ID = "44444444-4444-4444-4444-444444444444"
AGENT_ID = "55555555-5555-5555-5555-555555555555"

# Square zone in normalised space; edges at 0.1 and 0.9.
SQUARE = [(0.1, 0.1), (0.9, 0.1), (0.9, 0.9), (0.1, 0.9)]


def at(seconds: float) -> datetime:
    return T0 + timedelta(seconds=seconds)


def make_frame(seconds: float = 0.0, sequence: int = 0,
               camera_id: str = CAMERA_ID) -> Frame:
    return Frame(
        camera_id=camera_id,
        captured_at=at(seconds),
        image_ref=f"synthetic:{camera_id}:{sequence}",
        sequence=sequence,
    )


def make_config(
    *,
    is_active: bool = True,
    confidence_threshold: float = 0.5,
    debounce_seconds: int = 0,
    dwell_seconds: int | None = None,
    polygon: list[tuple[float, float]] | None = None,
    config_version: int = 1,
) -> AgentConfig:
    return AgentConfig(
        config_version=config_version,
        site_id=SITE_ID,
        cameras=[CameraConfig(camera_id=CAMERA_ID, name="Bay 3 entrance")],
        zones=[
            ZoneConfig(
                zone_id=ZONE_ID,
                camera_id=CAMERA_ID,
                name="Bay 3",
                polygon=polygon if polygon is not None else SQUARE,
            )
        ],
        rules=[
            RuleConfig(
                rule_id=RULE_ID,
                zone_id=ZONE_ID,
                rule_type="ppe_helmet",
                is_active=is_active,
                confidence_threshold=confidence_threshold,
                debounce_seconds=debounce_seconds,
                dwell_seconds=dwell_seconds,
                human_readable="Helmet required in Bay 3",
            )
        ],
    )


@pytest.fixture
def store(tmp_path: Path) -> Iterator[EdgeStore]:
    edge_store = EdgeStore(
        tmp_path / "edge.sqlite3",
        # [OPEN - OQ-4] values: tests choose small, explicit numbers.
        warning_bytes=4_000,
        critical_bytes=8_000,
    )
    yield edge_store
    edge_store.close()


class RecordingCounters:
    """CounterSink test double: records every increment, in order."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, str, str | None, object]] = []

    def increment_counter(
        self,
        bucket_start: str,
        camera_id: str,
        rule_id: str | None,
        counter: object,
    ) -> None:
        self.calls.append((bucket_start, camera_id, rule_id, counter))

    def kinds(self) -> list[object]:
        return [call[3] for call in self.calls]


class FakeControlPlane:
    """Scriptable control plane behind httpx.MockTransport.

    Response scripts are consumed in order; when a script list is empty the
    happy-path default applies (201 for ingest routes, 200 + document for
    config). An entry may be an int status or an Exception to raise as a
    transport failure.
    """

    def __init__(self, config_document: dict | None = None) -> None:
        self.auth_calls = 0
        self.auth_responses: list[int] = []
        self.event_responses: list[object] = []
        self.config_responses: list[object] = []
        self.config_document = config_document
        self.received_events: list[dict] = []
        self.received_gaps: list[dict] = []
        self.received_health: list[dict] = []
        self.request_log: list[tuple[str, str]] = []

    def handler(self, request):  # -> httpx.Response
        import json as _json

        import httpx

        path = request.url.path
        self.request_log.append((request.method, path))
        if path == "/api/v1/auth/agent":
            self.auth_calls += 1
            if self.auth_responses:
                status = self.auth_responses.pop(0)
                if status != 200:
                    return httpx.Response(status, json={"error": "denied"})
            return httpx.Response(
                200, json={"access_token": f"tok-{self.auth_calls}"}
            )
        if not request.headers.get("authorization", "").startswith("Bearer "):
            return httpx.Response(401, json={"error": "unauthenticated"})
        if path == "/api/v1/events":
            scripted = self.event_responses.pop(0) if self.event_responses else 201
            if isinstance(scripted, Exception):
                raise scripted
            body = _json.loads(request.content)
            if scripted in (200, 201):
                self.received_events.append(body)
                return httpx.Response(
                    scripted,
                    json={
                        "id": "88888888-8888-8888-8888-888888888888",
                        "event_id": body.get("event_id"),
                        "status": "unverified",
                        "received_at": "2026-08-12T09:00:01Z",
                    },
                )
            return httpx.Response(scripted, json={"error": f"scripted {scripted}"})
        if path == "/api/v1/coverage-gaps":
            self.received_gaps.append(_json.loads(request.content))
            return httpx.Response(201, json={})
        if path == "/api/v1/agents/health":
            self.received_health.append(_json.loads(request.content))
            return httpx.Response(201, json={})
        if path.startswith("/api/v1/agents/") and path.endswith("/config"):
            scripted = (
                self.config_responses.pop(0) if self.config_responses else None
            )
            if isinstance(scripted, Exception):
                raise scripted
            if isinstance(scripted, int):
                return httpx.Response(scripted, json={"error": "scripted"})
            if isinstance(scripted, dict):
                document = scripted
            else:
                document = self.config_document
            if document is None:
                return httpx.Response(404, json={"error": "no config"})
            etag = f'"{document.get("config_version")}"'
            if request.headers.get("if-none-match") == etag:
                return httpx.Response(304)
            return httpx.Response(200, json=document, headers={"ETag": etag})
        return httpx.Response(404, json={"error": f"unknown path {path}"})

    def client(self):  # -> httpx.Client
        import httpx

        return httpx.Client(transport=httpx.MockTransport(self.handler))
