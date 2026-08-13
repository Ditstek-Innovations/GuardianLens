"""Tenant provisioning — DATABASE.md 13.5.1.

Provisioning is CODE, NEVER A RUNBOOK. A hand-built tenant is the
schema-drift risk (R-9) arriving on day one, and the pilot runs the same
code path a hundredth tenant would use — a router and a provisioner
exercised for the first time at tenant two have never been tested.

The sequence, and its failure behaviour:

    1  create the database and its owner role      abort; nothing registered
    2  migrate to head from revision 0001          abort; drop; nothing registered
    3  insert the single tenant_identity row       abort; drop
    4  seed roles (done by revision 0001)          abort; drop
    5  create the evidence-store prefix            abort; drop
    6  register in the control database            status 'provisioning'
    7  run FF-11 attestation                       fail -> 'drifted', never 'active'
    8  bootstrap the site_admin user               password set at first login
    9  status 'active'                             the router may now bind

*** A tenant reaches 'active' only by passing step 7. ***
There is no path from "database created" to "serving traffic" that skips it.
"""

from __future__ import annotations

import os
import sys
import uuid
from pathlib import Path

import psycopg
from psycopg import sql

from guardian_lens.db.attestation import attest
from guardian_lens.db.urls import (
    admin_url,
    psycopg_url,
    sqlalchemy_url,
    tenant_database_name,
    tenant_url,
)

__all__ = ["ProvisioningError", "provision", "ensure_tenant", "deprovision", "main"]


class ProvisioningError(RuntimeError):
    """Raised when a step fails. The caller drops whatever was created."""


def _repo_root() -> Path:
    for parent in Path(__file__).resolve().parents:
        if (parent / "alembic.ini").is_file():
            return parent
    raise ProvisioningError("alembic.ini not found above this package")


def _database_exists(admin: str, name: str) -> bool:
    with psycopg.connect(psycopg_url(admin), autocommit=True) as conn:
        row = conn.execute(
            "SELECT 1 FROM pg_database WHERE datname = %s", (name,)
        ).fetchone()
        return row is not None


def _create_database(admin: str, name: str) -> None:
    # CREATE DATABASE cannot run inside a transaction block.
    with psycopg.connect(psycopg_url(admin), autocommit=True) as conn:
        conn.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(name)))


def _drop_database(admin: str, name: str) -> None:
    with psycopg.connect(psycopg_url(admin), autocommit=True) as conn:
        conn.execute(
            sql.SQL("DROP DATABASE IF EXISTS {} WITH (FORCE)").format(
                sql.Identifier(name)
            )
        )


def _migrate_to_head(url: str) -> None:
    from alembic import command
    from alembic.config import Config

    cfg = Config(str(_repo_root() / "alembic.ini"), ini_section="tenant")
    cfg.set_main_option("script_location", str(_repo_root() / "migrations" / "tenant"))
    previous = os.environ.get("GL_TENANT_DB_URL")
    os.environ["GL_TENANT_DB_URL"] = sqlalchemy_url(url)
    try:
        command.upgrade(cfg, "head")
    finally:
        if previous is None:
            os.environ.pop("GL_TENANT_DB_URL", None)
        else:
            os.environ["GL_TENANT_DB_URL"] = previous


def _write_identity(url: str, tenant_id: uuid.UUID, slug: str) -> None:
    with psycopg.connect(psycopg_url(url)) as conn:
        conn.execute(
            "INSERT INTO tenant_identity (tenant_id, tenant_slug) VALUES (%s, %s)",
            (str(tenant_id), slug),
        )
        conn.commit()


def _register(control_url: str, tenant_id: uuid.UUID, slug: str, name: str) -> None:
    with psycopg.connect(psycopg_url(control_url)) as conn:
        conn.execute(
            """
            INSERT INTO tenants (id, slug, display_name, status)
            VALUES (%s, %s, %s, 'provisioning')
            """,
            (str(tenant_id), slug, name),
        )
        conn.execute(
            """
            INSERT INTO control_audit_log (actor, action, tenant_id, after_state)
            VALUES (%s, 'tenant.provisioning', %s,
                    jsonb_build_object('slug', %s::text))
            """,
            (os.environ.get("USER", "system.provisioning"), str(tenant_id), slug),
        )
        conn.commit()


def _set_status(control_url: str, tenant_id: uuid.UUID, status: str) -> None:
    with psycopg.connect(psycopg_url(control_url)) as conn:
        conn.execute(
            """
            UPDATE tenants
               SET status = %s,
                   provisioned_at = COALESCE(
                       provisioned_at,
                       CASE WHEN %s = 'active' THEN now() END),
                   updated_at = now()
             WHERE id = %s
            """,
            (status, status, str(tenant_id)),
        )
        conn.execute(
            """
            INSERT INTO control_audit_log (actor, action, tenant_id, after_state)
            VALUES (%s, %s, %s, jsonb_build_object('status', %s::text))
            """,
            (
                os.environ.get("USER", "system.provisioning"),
                f"tenant.{status}",
                str(tenant_id),
                status,
            ),
        )
        conn.commit()


def provision(
    slug: str,
    display_name: str | None = None,
    *,
    base_url: str | None = None,
    control_url: str | None = None,
) -> uuid.UUID:
    """Provision one tenant. Returns its tenant id.

    Raises ProvisioningError and leaves nothing behind if any step before
    registration fails.
    """
    base_url = base_url or os.environ["GL_TENANT_DB_URL"]
    control_url = control_url or os.environ["GL_CONTROL_DB_URL"]
    display_name = display_name or slug

    db_name = tenant_database_name(slug)
    admin = admin_url(base_url)
    url = tenant_url(base_url, slug)
    tenant_id = uuid.uuid4()

    if _database_exists(admin, db_name):
        raise ProvisioningError(f"database {db_name} already exists")

    _create_database(admin, db_name)
    try:
        _migrate_to_head(url)                                    # steps 2, 4
        _write_identity(url, tenant_id, slug)                    # step 3
        _register(control_url, tenant_id, slug, display_name)    # step 6
    except Exception as exc:  # noqa: BLE001 — any failure before the tenant
        # is registered means drop. Leaving a database that nothing in the
        # control registry owns is worse than leaving nothing: it is invisible
        # to attestation, to backup scheduling and to deprovisioning.
        _drop_database(admin, db_name)
        raise ProvisioningError(f"provisioning {slug} failed: {exc}") from exc

    # Step 7. The gate. Nothing reaches 'active' without it.
    with psycopg.connect(psycopg_url(url)) as conn:
        result = attest(conn)
    if not result.ok:
        _set_status(control_url, tenant_id, "drifted")
        raise ProvisioningError(
            f"tenant {slug} failed FF-11 attestation and was left "
            f"'drifted', not 'active':\n{result.report()}"
        )

    _set_status(control_url, tenant_id, "active")                # step 9
    return tenant_id


def ensure_tenant(
    slug: str,
    display_name: str | None = None,
    *,
    base_url: str | None = None,
    control_url: str | None = None,
) -> uuid.UUID:
    """Provision-or-adopt, idempotently. The dev-bootstrap entry point.

    ``provision`` refuses an existing database, deliberately — a silent
    reuse in production would hand one customer another's data. But a dev
    machine accumulates half-states: a bare database left by an interrupted
    run, a migrated database whose registry row was never written, a
    registry row whose database was dropped by hand. This walks whichever
    state it finds to the one goal state:

        database at head + identity row + registry row + attested + active

    A slug/identity MISMATCH is the one state it refuses to repair: a
    database claiming to be a different tenant is exactly the misrouting
    ADR-016 exists to prevent, and no automatic fix is safe there.
    """
    base_url = base_url or os.environ["GL_TENANT_DB_URL"]
    control_url = control_url or os.environ["GL_CONTROL_DB_URL"]
    display_name = display_name or slug

    db_name = tenant_database_name(slug)
    admin = admin_url(base_url)
    url = tenant_url(base_url, slug)

    with psycopg.connect(psycopg_url(control_url)) as conn:
        row = conn.execute(
            "SELECT id, status FROM tenants WHERE slug = %s", (slug,)
        ).fetchone()

    if not _database_exists(admin, db_name):
        if row is not None:
            # Registry says the tenant exists; the database is gone. In dev
            # that means someone dropped it by hand — rebuild it under the
            # SAME tenant id so nothing referring to the id dangles.
            tenant_id = uuid.UUID(str(row[0]))
            _create_database(admin, db_name)
            try:
                _migrate_to_head(url)
                _write_identity(url, tenant_id, slug)
            except Exception as exc:  # noqa: BLE001
                _drop_database(admin, db_name)
                raise ProvisioningError(
                    f"rebuilding {slug} failed: {exc}"
                ) from exc
        else:
            return provision(
                slug, display_name, base_url=base_url, control_url=control_url
            )
    else:
        # Database exists (possibly empty, possibly behind head).
        _migrate_to_head(url)
        with psycopg.connect(psycopg_url(url)) as conn:
            identity = conn.execute(
                "SELECT tenant_id, tenant_slug FROM tenant_identity"
            ).fetchone()
        if identity is not None and identity[1] != slug:
            raise ProvisioningError(
                f"database {db_name} identifies as tenant "
                f"{identity[1]!r}, not {slug!r} — refusing to adopt "
                f"(ADR-016 anti-misrouting; resolve by hand)"
            )
        if identity is not None:
            tenant_id = uuid.UUID(str(identity[0]))
            if row is not None and uuid.UUID(str(row[0])) != tenant_id:
                raise ProvisioningError(
                    f"registry id and tenant_identity disagree for {slug} "
                    f"— refusing to adopt; resolve by hand"
                )
        else:
            tenant_id = uuid.UUID(str(row[0])) if row else uuid.uuid4()
            _write_identity(url, tenant_id, slug)

    if row is None:
        _register(control_url, tenant_id, slug, display_name)

    with psycopg.connect(psycopg_url(url)) as conn:
        result = attest(conn)
    if not result.ok:
        _set_status(control_url, tenant_id, "drifted")
        raise ProvisioningError(
            f"tenant {slug} failed FF-11 attestation and was left "
            f"'drifted', not 'active':\n{result.report()}"
        )
    _set_status(control_url, tenant_id, "active")
    return tenant_id


def deprovision(
    slug: str,
    *,
    base_url: str | None = None,
    control_url: str | None = None,
) -> None:
    """Drop a tenant database, retaining the registry row as a tombstone.

    Deleting the registry row alongside the database would erase the record
    that the tenant ever existed, including the audited fact of the deletion.
    The data goes; the fact of its deletion does not.
    """
    base_url = base_url or os.environ["GL_TENANT_DB_URL"]
    control_url = control_url or os.environ["GL_CONTROL_DB_URL"]

    _drop_database(admin_url(base_url), tenant_database_name(slug))

    with psycopg.connect(psycopg_url(control_url)) as conn:
        # The login directory must not outlive the tenant: an orphaned hash
        # routes an address to a database that no longer exists AND blocks
        # that address from ever joining another tenant. The tenants row is
        # the tombstone (the fact of deletion); the directory rows are data.
        conn.execute(
            """
            DELETE FROM user_directory
             WHERE tenant_id = (SELECT id FROM tenants WHERE slug = %s)
            """,
            (slug,),
        )
        conn.execute(
            """
            UPDATE tenants
               SET status = 'deprovisioned', deleted_at = now(), updated_at = now()
             WHERE slug = %s
            """,
            (slug,),
        )
        conn.execute(
            """
            INSERT INTO control_audit_log (actor, action, tenant_id, after_state)
            SELECT %s, 'tenant.deprovisioned', id,
                   jsonb_build_object('slug', slug)
              FROM tenants WHERE slug = %s
            """,
            (os.environ.get("USER", "system.provisioning"), slug),
        )
        conn.commit()


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if len(argv) < 2 or argv[0] not in {"provision", "deprovision"}:
        print(
            "usage: python -m guardian_lens.db.provisioning "
            "provision|deprovision <slug> [display name]",
            file=sys.stderr,
        )
        return 2

    action, slug = argv[0], argv[1]
    try:
        if action == "provision":
            tenant_id = provision(slug, " ".join(argv[2:]) or None)
            print(f"provisioned {slug} as {tenant_id} — status active")
        else:
            deprovision(slug)
            print(f"deprovisioned {slug} — registry row retained as tombstone")
    except ProvisioningError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
