"""Fixtures for the bypass suite.

The suite runs against a real PostgreSQL database, deliberately. Its whole
purpose is to prove that the data layer refuses invalid states *by itself* —
the fourth enforcement layer in ARCHITECTURE.md 4.2, the one that survives a
direct SQL connection when the first three have been refactored away. A
mocked database would test nothing.
"""

from __future__ import annotations

import os
import uuid
from collections.abc import Iterator

import psycopg
import pytest

from guardian_lens.db.provisioning import deprovision, provision
from guardian_lens.db.urls import psycopg_url, tenant_url

TENANT_PREFIX = "bypass"
CONTROL_URL_ENV = "GL_CONTROL_DB_URL"
BASE_URL_ENV = "GL_TENANT_DB_URL"


def _require(var: str) -> str:
    value = os.environ.get(var)
    if not value:
        pytest.skip(f"{var} is not set; run `make up` and source .env")
    return value


@pytest.fixture(scope="session")
def control_url() -> str:
    return _require(CONTROL_URL_ENV)


@pytest.fixture(scope="session")
def tenant_slug() -> str:
    """A fresh slug per run.

    Registry rows are never deleted — deprovisioning retains a tombstone, and
    control_audit_log is append-only, so an earlier run's rows cannot be
    cleaned up even in a test. (The suite discovered this the first time it
    ran: the append-only trigger refused the fixture's own DELETE, which is
    the trigger working.) A unique slug means the real lifecycle is exercised
    without ever needing to erase history.
    """
    return f"{TENANT_PREFIX}_{uuid.uuid4().hex[:8]}"


@pytest.fixture(scope="session")
def tenant_db_url(control_url: str, tenant_slug: str) -> Iterator[str]:
    """A freshly provisioned tenant database, dropped afterwards.

    Provisioned through the real code path (DATABASE.md 13.5.1), not by
    hand — a hand-built test tenant would not exercise the thing most likely
    to drift in production, and would skip the FF-11 gate at step 7.
    """
    base = _require(BASE_URL_ENV)
    provision(tenant_slug, "Bypass suite", base_url=base, control_url=control_url)
    yield tenant_url(base, tenant_slug)
    deprovision(tenant_slug, base_url=base, control_url=control_url)


@pytest.fixture
def db(tenant_db_url: str) -> Iterator[psycopg.Connection]:
    """A connection whose work is always rolled back.

    Each test attempts a violation and asserts the database refuses. Nothing
    a test writes should outlive it.
    """
    conn = psycopg.connect(psycopg_url(tenant_db_url))
    try:
        yield conn
    finally:
        conn.rollback()
        conn.close()


@pytest.fixture
def control_db(control_url: str) -> Iterator[psycopg.Connection]:
    conn = psycopg.connect(psycopg_url(control_url))
    try:
        yield conn
    finally:
        conn.rollback()
        conn.close()


@pytest.fixture
def seed(db: psycopg.Connection) -> dict[str, uuid.UUID]:
    """A minimal configured graph: site, camera, zone, active rule, agent,
    model version, reviewer.

    Note the rule is created INACTIVE and then activated with a named user,
    because chk_active_rule_has_activator makes any other order impossible —
    which is BR-C-02 working as intended.
    """
    ids = {k: uuid.uuid4() for k in ("site", "camera", "zone", "rule", "agent",
                                     "model", "user")}
    with db.cursor() as cur:
        cur.execute(
            "INSERT INTO users (id, email, full_name, password_hash) "
            "VALUES (%s, %s, %s, %s)",
            (ids["user"], f"reviewer+{ids['user']}@example.test",
             "Test Reviewer", "argon2id$placeholder"),
        )
        cur.execute(
            "INSERT INTO sites (id, name, timezone) VALUES (%s, %s, %s)",
            (ids["site"], "Test Site", "Asia/Kolkata"),
        )
        cur.execute(
            """
            INSERT INTO cameras (id, site_id, name, stream_url_encrypted,
                                 stream_url_key_id)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (ids["camera"], ids["site"], "Bay 3 entrance",
             b"\x00ciphertext-placeholder", "key-1"),
        )
        cur.execute(
            "INSERT INTO zones (id, camera_id, name, polygon) "
            "VALUES (%s, %s, %s, %s)",
            (ids["zone"], ids["camera"], "Bay 3",
             '[[0.1,0.1],[0.9,0.1],[0.9,0.9],[0.1,0.9]]'),
        )
        cur.execute(
            """
            INSERT INTO detection_rules
                (id, zone_id, rule_type, confidence_threshold,
                 debounce_seconds, human_readable, created_by,
                 is_active, activated_by, activated_at)
            VALUES (%s, %s, 'ppe_helmet', 0.500, 30,
                    'Helmet required in Bay 3', %s, TRUE, %s, now())
            """,
            (ids["rule"], ids["zone"], ids["user"], ids["user"]),
        )
        cur.execute(
            "INSERT INTO agents (id, site_id, name, credential_hash) "
            "VALUES (%s, %s, %s, %s)",
            (ids["agent"], ids["site"], "edge-1", "argon2id$placeholder"),
        )
        cur.execute(
            "INSERT INTO model_versions (id, version, artefact_hash, classes) "
            "VALUES (%s, %s, %s, %s)",
            # Unique per invocation. A fixed version made any test that
            # committed poison every later one through uq_model_versions_version.
            (ids["model"], f"0.1.0-{ids['model'].hex[:8]}",
             "sha256:placeholder", '["helmet"]'),
        )
    return ids


def insert_event(
    db: psycopg.Connection,
    seed: dict[str, uuid.UUID],
    **overrides: object,
) -> uuid.UUID:
    """Insert a valid unverified candidate event and return its id."""
    event_pk = overrides.pop("id", uuid.uuid4())
    columns: dict[str, object] = {
        "id": event_pk,
        "event_id": uuid.uuid4(),
        "site_id": seed["site"],
        "camera_id": seed["camera"],
        "zone_id": seed["zone"],
        "rule_id": seed["rule"],
        "rule_snapshot": '{"rule_type":"ppe_helmet","threshold":0.5}',
        "agent_id": seed["agent"],
        "model_version_id": seed["model"],
        "confidence": 0.9,
        "occurred_at": "2026-08-12T09:00:00+00:00",
        "evidence_ref": "evidence/test/frame.jpg",
    }
    columns.update(overrides)
    names = ", ".join(columns)
    placeholders = ", ".join(["%s"] * len(columns))
    with db.cursor() as cur:
        cur.execute(
            f"INSERT INTO events ({names}) VALUES ({placeholders})",
            tuple(columns.values()),
        )
    return event_pk
