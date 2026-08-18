"""Health endpoints (TRD 10.7) and the bootstrap CLI."""

from __future__ import annotations

import uuid

import psycopg
import pytest

from guardian_lens.api.bootstrap import bootstrap, main as bootstrap_main
from guardian_lens.db.urls import psycopg_url
from guardian_lens.tenancy.registry import email_hash


def test_health_is_unauthenticated(client):
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["version"]


def test_readiness_reports_dependency_checks(client):
    response = client.get("/api/v1/health/ready")
    assert response.status_code == 200
    body = response.json()
    assert body["checks"]["database"] == "ok"
    assert body["checks"]["evidence_store"] == "ok"


def test_bootstrap_creates_admin_site_grant_and_directory(
    client, tenant_slug, tenant_db_url, control_url, monkeypatch, api_seed
):
    """The CLI path end-to-end: after bootstrap, the admin can log in
    through the real login flow and holds site_admin."""
    email = f"first-admin+{tenant_slug}@example.test"
    password = "chosen-by-operator-9!"
    monkeypatch.setenv("GL_BOOTSTRAP_PASSWORD", password)

    user_id = bootstrap(
        tenant_slug,
        email,
        "First Admin",
        site_name="Bootstrap Plant",
        timezone_name="Asia/Kolkata",
        control_url=control_url,
    )

    with psycopg.connect(psycopg_url(tenant_db_url)) as conn:
        site = conn.execute(
            "SELECT id FROM sites WHERE name = 'Bootstrap Plant'"
        ).fetchone()
        assert site is not None
        grant = conn.execute(
            "SELECT r.name FROM user_roles ur JOIN roles r ON r.id = ur.role_id"
            " WHERE ur.user_id = %s AND ur.site_id = %s",
            (str(user_id), site[0]),
        ).fetchone()
        assert grant == ("site_admin",)
        actions = {
            row[0]
            for row in conn.execute(
                "SELECT action FROM audit_log WHERE actor_user_id = %s",
                (str(user_id),),
            ).fetchall()
        }
        assert {"site.created", "user.created", "user.role_granted"} <= actions
        stored_hash = conn.execute(
            "SELECT password_hash FROM users WHERE id = %s", (str(user_id),)
        ).fetchone()[0]
        assert password not in stored_hash  # Argon2id, never plaintext

    with psycopg.connect(psycopg_url(control_url)) as conn:
        directory = conn.execute(
            "SELECT tenant_id FROM user_directory WHERE email_hash = %s",
            (email_hash(email),),
        ).fetchone()
        assert directory is not None

    login = client.post(
        "/api/v1/auth/login", json={"email": email, "password": password}
    )
    assert login.status_code == 200
    assert "site_admin" in login.json()["user"]["roles"]


def test_bootstrap_generates_a_password_when_none_is_supplied(
    tenant_slug, control_url, monkeypatch, capsys, api_seed
):
    """No default credential, ever: absent GL_BOOTSTRAP_PASSWORD, a random
    password is generated and printed exactly once."""
    monkeypatch.delenv("GL_BOOTSTRAP_PASSWORD", raising=False)
    email = f"generated-admin+{uuid.uuid4().hex[:8]}@example.test"
    bootstrap(
        tenant_slug,
        email,
        "Generated Admin",
        site_name=f"Site {uuid.uuid4().hex[:6]}",
        timezone_name="Asia/Kolkata",
        control_url=control_url,
    )
    out = capsys.readouterr().out
    assert "generated admin password: " in out


def test_bootstrap_cli_reports_failure_for_unknown_tenant(
    control_url, monkeypatch, capsys
):
    monkeypatch.setenv("GL_BOOTSTRAP_PASSWORD", "irrelevant-1!")
    exit_code = bootstrap_main(
        [
            "tenant_that_never_existed",
            "x@example.test",
            "X",
            "--site-name",
            "S",
            "--timezone",
            "UTC",
        ]
    )
    assert exit_code == 1
    assert "bootstrap failed" in capsys.readouterr().err
