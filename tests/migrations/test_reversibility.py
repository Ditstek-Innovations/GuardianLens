"""Migration reversibility and the provisioning lifecycle.

DATABASE.md 13.1: production is forward-only. `downgrade()` exists so a
revision is reversible in development and TESTABLE IN CI — an untested
downgrade is a comment, and a revision nobody can unwind is one nobody can
safely review either.
"""

from __future__ import annotations

import os
import uuid
from collections.abc import Iterator

import psycopg
import pytest

from guardian_lens.db.attestation import attest
from guardian_lens.db.provisioning import (
    ProvisioningError,
    _migrate_to_head,
    deprovision,
    provision,
)
from guardian_lens.db.urls import (
    admin_url,
    psycopg_url,
    tenant_database_name,
    tenant_url,
)


@pytest.fixture
def scratch_slug(control_url: str) -> Iterator[str]:
    """A tenant this test owns outright, torn down whatever happens."""
    slug = f"scratch_{uuid.uuid4().hex[:8]}"
    yield slug
    base = os.environ["GL_TENANT_DB_URL"]
    try:
        deprovision(slug, base_url=base, control_url=control_url)
    except Exception:  # noqa: BLE001 — nothing provisioned is a normal outcome
        pass


def _alembic(url: str, target: str) -> None:
    from alembic import command
    from alembic.config import Config
    from pathlib import Path

    root = Path(__file__).resolve().parents[2]
    cfg = Config(str(root / "alembic.ini"), ini_section="tenant")
    cfg.set_main_option("script_location", str(root / "migrations" / "tenant"))
    previous = os.environ.get("GL_TENANT_DB_URL")
    os.environ["GL_TENANT_DB_URL"] = url
    try:
        (command.upgrade if target == "head" else command.downgrade)(cfg, target)
    finally:
        if previous is None:
            os.environ.pop("GL_TENANT_DB_URL", None)
        else:
            os.environ["GL_TENANT_DB_URL"] = previous


def test_every_revision_reverses_and_reapplies(scratch_slug, control_url):
    """head -> base -> head, then attest.

    The round trip is the point. A downgrade that leaves an orphaned trigger
    or function makes the next upgrade fail in a way that only appears on a
    machine someone has been developing on for a month.
    """
    base = os.environ["GL_TENANT_DB_URL"]
    provision(scratch_slug, "Scratch", base_url=base, control_url=control_url)
    url = tenant_url(base, scratch_slug)

    _alembic(url, "base")
    with psycopg.connect(psycopg_url(url)) as conn:
        remaining = conn.execute(
            """
            SELECT count(*) FROM information_schema.tables
             WHERE table_schema = 'public'
               AND table_name <> 'alembic_version_tenant'
            """
        ).fetchone()[0]
    assert remaining == 0, "downgrade left tables behind"

    _alembic(url, "head")
    with psycopg.connect(psycopg_url(url)) as conn:
        result = attest(conn)
    assert result.ok, result.report()
    assert not result.failures, result.report()


def test_downgrade_removes_trigger_functions_too(scratch_slug, control_url):
    """A dropped table leaves its trigger function behind unless the
    downgrade says otherwise, and CREATE OR REPLACE then silently masks the
    difference between a clean and a dirty database."""
    base = os.environ["GL_TENANT_DB_URL"]
    provision(scratch_slug, "Scratch", base_url=base, control_url=control_url)
    url = tenant_url(base, scratch_slug)

    _alembic(url, "base")
    with psycopg.connect(psycopg_url(url)) as conn:
        functions = conn.execute(
            """
            SELECT proname FROM pg_proc p
              JOIN pg_namespace n ON n.oid = p.pronamespace
             WHERE n.nspname = 'public' AND proname LIKE 'fn_%'
            """
        ).fetchall()
    assert functions == [], f"orphaned functions after downgrade: {functions}"


def test_provisioning_is_idempotent_by_refusal(scratch_slug, control_url):
    """Provisioning the same slug twice must fail loudly, not quietly
    reuse. A silent reuse would hand a second customer the first one's
    database — the exact outcome ADR-016 exists to prevent."""
    base = os.environ["GL_TENANT_DB_URL"]
    provision(scratch_slug, "Scratch", base_url=base, control_url=control_url)
    with pytest.raises(ProvisioningError, match="already exists"):
        provision(scratch_slug, "Scratch again", base_url=base, control_url=control_url)


def test_an_invalid_slug_creates_nothing(control_url):
    """The validator runs before anything is created, so a bad slug cannot
    leave an orphaned database. Its pattern is identical to
    chk_tenants_slug_format in migration c0001."""
    base = os.environ["GL_TENANT_DB_URL"]
    with pytest.raises(ValueError):
        provision("Not A Valid Slug", base_url=base, control_url=control_url)

    with psycopg.connect(psycopg_url(admin_url(base)), autocommit=True) as conn:
        leftovers = conn.execute(
            "SELECT count(*) FROM pg_database WHERE datname LIKE 'gl_tenant_Not%'"
        ).fetchone()[0]
    assert leftovers == 0


def test_a_tenant_failing_attestation_is_left_drifted_not_active(
    scratch_slug, control_url, monkeypatch
):
    """DATABASE.md 13.5.1 step 7 — the gate.

    A tenant reaches 'active' only by passing attestation. This simulates a
    fan-out that reported success against a database missing a constraint,
    which is risk R-9's exact shape: the migration says yes, the schema says
    no, and only the schema matters.
    """
    from guardian_lens.db import provisioning as prov

    class _Failed:
        ok = False
        blocking_failures = ["chk_decided_requires_reviewer"]

        def report(self) -> str:
            return "simulated drift"

    monkeypatch.setattr(prov, "attest", lambda conn: _Failed())

    base = os.environ["GL_TENANT_DB_URL"]
    with pytest.raises(ProvisioningError, match="drifted"):
        provision(scratch_slug, "Scratch", base_url=base, control_url=control_url)

    with psycopg.connect(psycopg_url(control_url)) as conn:
        status, provisioned = conn.execute(
            "SELECT status, provisioned_at FROM tenants WHERE slug = %s",
            (scratch_slug,),
        ).fetchone()
    assert status == "drifted"
    assert provisioned is None, "a drifted tenant must never look provisioned"


def test_deprovisioning_drops_the_database_and_keeps_the_tombstone(
    scratch_slug, control_url
):
    """The data goes; the fact of its deletion does not.

    Deleting the registry row alongside the database would erase the record
    that the tenant ever existed, including the audited fact of the deletion
    — BR-009 applied one level above the schema.
    """
    base = os.environ["GL_TENANT_DB_URL"]
    provision(scratch_slug, "Scratch", base_url=base, control_url=control_url)
    deprovision(scratch_slug, base_url=base, control_url=control_url)

    with psycopg.connect(psycopg_url(admin_url(base)), autocommit=True) as conn:
        exists = conn.execute(
            "SELECT count(*) FROM pg_database WHERE datname = %s",
            (tenant_database_name(scratch_slug),),
        ).fetchone()[0]
    assert exists == 0

    with psycopg.connect(psycopg_url(control_url)) as conn:
        status, deleted_at = conn.execute(
            "SELECT status, deleted_at FROM tenants WHERE slug = %s", (scratch_slug,)
        ).fetchone()
        audited = conn.execute(
            """
            SELECT count(*) FROM control_audit_log
             WHERE action = 'tenant.deprovisioned'
               AND tenant_id = (SELECT id FROM tenants WHERE slug = %s)
            """,
            (scratch_slug,),
        ).fetchone()[0]
    assert status == "deprovisioned"
    assert deleted_at is not None
    assert audited == 1, "the deletion itself was not recorded"
