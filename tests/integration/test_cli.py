"""The command-line entry points.

`make attest` and `make provision` are how a human touches this system
today, and the exit codes are what CI reads. An attestation that reports a
failure and exits 0 is worse than no attestation: the pipeline goes green
over a tenant whose rule enforcement is missing.
"""

from __future__ import annotations

import os
import uuid

import psycopg
import pytest

from guardian_lens.db import attestation, provisioning
from guardian_lens.db.urls import psycopg_url, tenant_url


def test_attestation_cli_without_a_url_explains_itself(capsys, monkeypatch):
    monkeypatch.delenv("GL_TENANT_DB_URL", raising=False)
    assert attestation.main([]) == 2
    assert "usage" in capsys.readouterr().err


def test_attestation_cli_exits_zero_on_a_healthy_tenant(tenant_db_url, capsys):
    assert attestation.main([tenant_db_url]) == 0
    out = capsys.readouterr().out
    assert "0 failing" in out
    assert "all present and enabled" in out


def test_attestation_cli_exits_nonzero_on_a_drifted_tenant(
    tenant_db_url, capsys
):
    """CI reads the exit code. A drifted tenant must fail the build."""
    with psycopg.connect(psycopg_url(tenant_db_url), autocommit=True) as conn:
        conn.execute("ALTER TABLE audit_log DISABLE TRIGGER trg_audit_append_only")
    try:
        assert attestation.main([tenant_db_url]) == 1
        out = capsys.readouterr().out
        assert "BLOCKING" in out
        assert "trg_audit_append_only" in out
        assert "DISABLED" in out
    finally:
        with psycopg.connect(psycopg_url(tenant_db_url), autocommit=True) as conn:
            conn.execute("ALTER TABLE audit_log ENABLE TRIGGER trg_audit_append_only")


def test_provisioning_cli_rejects_an_unknown_action(capsys):
    assert provisioning.main(["destroy", "acme"]) == 2
    assert "usage" in capsys.readouterr().err


def test_provisioning_cli_requires_a_slug(capsys):
    assert provisioning.main(["provision"]) == 2


def test_provisioning_cli_round_trip(control_url, capsys):
    """provision -> attest -> deprovision, through the CLI a human uses."""
    slug = f"cli_{uuid.uuid4().hex[:8]}"
    base = os.environ["GL_TENANT_DB_URL"]
    monkey = {"GL_TENANT_DB_URL": base, "GL_CONTROL_DB_URL": control_url}
    os.environ.update(monkey)

    assert provisioning.main(["provision", slug, "CLI", "tenant"]) == 0
    assert "status active" in capsys.readouterr().out

    assert attestation.main([tenant_url(base, slug)]) == 0
    capsys.readouterr()

    assert provisioning.main(["deprovision", slug]) == 0
    assert "tombstone" in capsys.readouterr().out


def test_provisioning_cli_reports_failure_without_a_traceback(control_url, capsys):
    """A duplicate slug is an operator error, not a crash. It gets a
    sentence and exit 1, because an operator reading a traceback learns
    less than one reading 'database gl_tenant_x already exists'."""
    slug = f"cli_{uuid.uuid4().hex[:8]}"
    base = os.environ["GL_TENANT_DB_URL"]
    os.environ["GL_CONTROL_DB_URL"] = control_url
    try:
        assert provisioning.main(["provision", slug]) == 0
        capsys.readouterr()
        assert provisioning.main(["provision", slug]) == 1
        assert "already exists" in capsys.readouterr().err
    finally:
        provisioning.deprovision(slug, base_url=base, control_url=control_url)
