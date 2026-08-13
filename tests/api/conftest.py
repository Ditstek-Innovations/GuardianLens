"""Fixtures for the API suite.

Runs against a REAL provisioned tenant — the session fixtures in
tests/conftest.py provision it through the production code path, FF-11
gate included. The app under test is the real factory output; tokens are
obtained through the real login and agent-exchange flows, so every test
exercises the same path a browser or edge agent would.

This file ADDS fixtures; tests/conftest.py is not modified.
"""

from __future__ import annotations

import base64
import os
import uuid
from collections.abc import Iterator
from typing import Any

import psycopg
import pytest
from argon2 import PasswordHasher
from fastapi.testclient import TestClient

from guardian_lens.api.app import create_app
from guardian_lens.core.settings import Settings
from guardian_lens.db.urls import psycopg_url
from guardian_lens.tenancy.registry import email_hash

PASSWORD = "a-long-test-password-9!"
WRONG_PASSWORD = "not-the-password-at-all"
AGENT_SECRET = "edge-agent-shared-secret-for-tests"

_hasher = PasswordHasher()

# Argon2 hashing is deliberately slow; hash the two test secrets once.
_PASSWORD_HASH = _hasher.hash(PASSWORD)
_AGENT_HASH = _hasher.hash(AGENT_SECRET)

ROLE_IDS = {
    "reviewer": "11111111-1111-4111-8111-111111111111",
    "safety_manager": "22222222-2222-4222-8222-222222222222",
    "site_admin": "33333333-3333-4333-8333-333333333333",
    "auditor": "44444444-4444-4444-8444-444444444444",
}

# A JPEG-looking frame; nothing validates image content at MVP.
FRAME_BYTES = b"\xff\xd8\xff\xe0" + b"guardian-lens-test-frame" * 4 + b"\xff\xd9"


@pytest.fixture(scope="session")
def api_settings(
    tenant_db_url: str, control_url: str, tmp_path_factory: pytest.TempPathFactory
) -> Settings:
    """Settings for the app under test. The tenant BASE url comes from the
    environment; the router derives the provisioned tenant's database from
    its slug, exactly as production would."""
    return Settings(
        control_db_url=control_url,
        tenant_db_url=os.environ["GL_TENANT_DB_URL"],
        jwt_secret="api-test-signing-secret-0123456789abcdef",
        evidence_root=str(tmp_path_factory.mktemp("evidence")),
        # Small limit so the 413 path is testable without megabyte bodies.
        evidence_max_bytes=64 * 1024,
    )


@pytest.fixture(scope="session")
def app(api_settings: Settings):
    return create_app(api_settings)


@pytest.fixture(scope="session")
def client(app) -> Iterator[TestClient]:
    # raise_server_exceptions=False: the rollback tests assert the 500
    # ENVELOPE, not a re-raised exception.
    with TestClient(app, raise_server_exceptions=False) as test_client:
        yield test_client


@pytest.fixture(autouse=True)
def _fresh_login_limiter(app) -> None:
    """The auth limiters are per-IP and TestClient is one IP; without a
    reset, earlier tests' requests would starve later ones."""
    app.state.login_limiter.reset()
    app.state.signup_limiter.reset()
    app.state.reset_request_limiter.reset()
    app.state.reset_limiter.reset()


@pytest.fixture(scope="session")
def api_seed(
    tenant_db_url: str, control_url: str, tenant_slug: str
) -> dict[str, Any]:
    """A COMMITTED configuration graph: two sites (for cross-site scope
    tests), users for each role, agents at both sites, an active rule and
    a registered model version. Login directory entries in the control DB.

    Committed deliberately, unlike the bypass suite's rollback fixture:
    the API operates over real transactions, and its writes are cleaned up
    by the session-scoped deprovision (the whole database is dropped).
    """
    ids: dict[str, Any] = {
        key: uuid.uuid4()
        for key in (
            "site_a", "site_b",
            "camera_a", "camera_b",
            "zone_a", "zone_a2", "zone_b",
            "rule_a", "rule_b",
            "agent_a", "agent_b",
            "model",
            "admin", "reviewer_a", "manager_a", "auditor_a",
        )
    }
    ids["emails"] = {
        name: f"{name.replace('_', '-')}+{tenant_slug}@example.test"
        for name in ("admin", "reviewer_a", "manager_a", "auditor_a")
    }
    ids["model_version"] = f"1.2.0-{tenant_slug}"

    with psycopg.connect(psycopg_url(tenant_db_url)) as conn:
        cur = conn.cursor()
        for name, tz in (("site_a", "Asia/Kolkata"), ("site_b", "Asia/Kolkata")):
            cur.execute(
                "INSERT INTO sites (id, name, timezone) VALUES (%s, %s, %s)",
                (ids[name], f"Test {name}", tz),
            )
        for cam, site in (("camera_a", "site_a"), ("camera_b", "site_b")):
            cur.execute(
                "INSERT INTO cameras (id, site_id, name, stream_url_encrypted,"
                " stream_url_key_id) VALUES (%s, %s, %s, %s, %s)",
                (ids[cam], ids[site], f"{cam} entrance",
                 b"\x00seed-ciphertext", "key-1"),
            )
        for zone, cam in (
            ("zone_a", "camera_a"), ("zone_a2", "camera_a"), ("zone_b", "camera_b")
        ):
            cur.execute(
                "INSERT INTO zones (id, camera_id, name, polygon)"
                " VALUES (%s, %s, %s, %s)",
                (ids[zone], ids[cam], zone,
                 "[[0.1,0.1],[0.9,0.1],[0.9,0.9],[0.1,0.9]]"),
            )
        for name, email in ids["emails"].items():
            cur.execute(
                "INSERT INTO users (id, email, full_name, password_hash)"
                " VALUES (%s, %s, %s, %s)",
                (ids[name], email, f"Test {name}", _PASSWORD_HASH),
            )
        grants = [
            ("admin", "site_admin", "site_a"),
            ("admin", "site_admin", "site_b"),
            ("reviewer_a", "reviewer", "site_a"),
            ("manager_a", "safety_manager", "site_a"),
            ("auditor_a", "auditor", "site_a"),
        ]
        for user, role, site in grants:
            cur.execute(
                "INSERT INTO user_roles (user_id, role_id, site_id, granted_by)"
                " VALUES (%s, %s, %s, %s)",
                (ids[user], ROLE_IDS[role], ids[site], ids["admin"]),
            )
        for rule, zone in (("rule_a", "zone_a"), ("rule_b", "zone_b")):
            cur.execute(
                "INSERT INTO detection_rules (id, zone_id, rule_type,"
                " confidence_threshold, debounce_seconds, human_readable,"
                " created_by, is_active, activated_by, activated_at)"
                " VALUES (%s, %s, 'ppe_helmet', 0.500, 30,"
                " 'Helmet required', %s, TRUE, %s, now())",
                (ids[rule], ids[zone], ids["admin"], ids["admin"]),
            )
        for agent, site in (("agent_a", "site_a"), ("agent_b", "site_b")):
            cur.execute(
                "INSERT INTO agents (id, site_id, name, credential_hash)"
                " VALUES (%s, %s, %s, %s)",
                (ids[agent], ids[site], agent, _AGENT_HASH),
            )
        cur.execute(
            "INSERT INTO model_versions (id, version, artefact_hash, classes)"
            " VALUES (%s, %s, 'sha256:test', '[\"helmet\"]')",
            (ids["model"], ids["model_version"]),
        )
        conn.commit()

    with psycopg.connect(psycopg_url(control_url)) as conn:
        for email in ids["emails"].values():
            conn.execute(
                "INSERT INTO user_directory (email_hash, tenant_id)"
                " SELECT %s, id FROM tenants WHERE slug = %s",
                (email_hash(email), tenant_slug),
            )
        conn.commit()
    return ids


# -- tokens, through the real flows ------------------------------------------


def _login(client: TestClient, email: str) -> dict[str, Any]:
    response = client.post(
        "/api/v1/auth/login", json={"email": email, "password": PASSWORD}
    )
    assert response.status_code == 200, response.text
    return response.json()


@pytest.fixture(scope="session")
def admin_token(client: TestClient, api_seed: dict[str, Any]) -> str:
    return _login(client, api_seed["emails"]["admin"])["access_token"]


@pytest.fixture(scope="session")
def reviewer_token(client: TestClient, api_seed: dict[str, Any]) -> str:
    return _login(client, api_seed["emails"]["reviewer_a"])["access_token"]


@pytest.fixture(scope="session")
def manager_token(client: TestClient, api_seed: dict[str, Any]) -> str:
    return _login(client, api_seed["emails"]["manager_a"])["access_token"]


@pytest.fixture(scope="session")
def auditor_token(client: TestClient, api_seed: dict[str, Any]) -> str:
    return _login(client, api_seed["emails"]["auditor_a"])["access_token"]


def _agent_token(
    client: TestClient, tenant_slug: str, agent_id: uuid.UUID
) -> str:
    response = client.post(
        "/api/v1/auth/agent",
        json={"credential": f"{tenant_slug}:{agent_id}:{AGENT_SECRET}"},
    )
    assert response.status_code == 200, response.text
    return response.json()["access_token"]


@pytest.fixture(scope="session")
def agent_token(
    client: TestClient, api_seed: dict[str, Any], tenant_slug: str
) -> str:
    return _agent_token(client, tenant_slug, api_seed["agent_a"])


@pytest.fixture(scope="session")
def agent_b_token(
    client: TestClient, api_seed: dict[str, Any], tenant_slug: str
) -> str:
    return _agent_token(client, tenant_slug, api_seed["agent_b"])


def bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def ingest_payload(api_seed: dict[str, Any], **overrides: Any) -> dict[str, Any]:
    """A valid TRD 10.3 ingest body for site A with a fresh event_id."""
    payload: dict[str, Any] = {
        "event_id": str(uuid.uuid4()),
        "camera_id": str(api_seed["camera_a"]),
        "zone_id": str(api_seed["zone_a"]),
        "rule_id": str(api_seed["rule_a"]),
        "rule_snapshot": {
            "rule_type": "ppe_helmet",
            "threshold": 0.5,
            "human_readable": "Helmet required",
        },
        "source": "guardian_lens",
        "model_version": api_seed["model_version"],
        "confidence": 0.81,
        "occurred_at": "2026-08-12T09:00:00Z",
        "evidence": {
            "content_type": "image/jpeg",
            "blurred": False,
            "data_b64": base64.b64encode(FRAME_BYTES).decode(),
        },
    }
    payload.update(overrides)
    return payload


def create_unverified_event(
    client: TestClient,
    api_seed: dict[str, Any],
    token: str,
    **overrides: Any,
) -> str:
    """Ingest one event through the API; returns its server-side id."""
    response = client.post(
        "/api/v1/events",
        json=ingest_payload(api_seed, **overrides),
        headers=bearer(token),
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


@pytest.fixture
def tenant_conn(tenant_db_url: str) -> Iterator[psycopg.Connection]:
    """Read-only inspection connection for asserting persisted state."""
    conn = psycopg.connect(psycopg_url(tenant_db_url))
    try:
        yield conn
    finally:
        conn.rollback()
        conn.close()
