"""Bootstrap the first site and admin of a provisioned tenant.

    python -m guardian_lens.api.bootstrap <slug> <email> <full_name> \
        --site-name "Plant 1" --timezone "Asia/Kolkata"

Provisioning (db/provisioning.py) creates the database and its schema;
this creates the first HUMAN inside it: site, admin user, site_admin
grant, the control-database login directory entry, and the audit entries —
one transaction per database, because the two databases cannot share one.
The tenant transaction commits first; a directory entry pointing at a
user that does not exist would break login, while a user without a
directory entry is repaired by re-running bootstrap.

The password comes from GL_BOOTSTRAP_PASSWORD or is generated and printed
ONCE. There is no default credential at any phase (TRD 12.6 A05), and the
password is never logged or stored anywhere but as an Argon2id hash.

The tenant session comes from the real registry + router path, so the
tenant_identity assertion protects bootstrap exactly as it protects a
request: bootstrapping an admin into the wrong database is the same
incident as serving from it.
"""

from __future__ import annotations

import argparse
import os
import secrets
import sys
import uuid

import psycopg
import sqlalchemy as sa
from argon2 import PasswordHasher

from guardian_lens.core.errors import GuardianError
from guardian_lens.db.urls import psycopg_url
from guardian_lens.repositories.audit import AuditRepository
from guardian_lens.repositories.identity import IdentityRepository
from guardian_lens.repositories.tables import sites, users
from guardian_lens.services.audit import AuditService
from guardian_lens.tenancy.registry import TenantRegistry, email_hash
from guardian_lens.tenancy.router import TenantRouter

__all__ = ["bootstrap", "main"]


def bootstrap(
    slug: str,
    email: str,
    full_name: str,
    *,
    site_name: str,
    timezone_name: str,
    control_url: str | None = None,
    base_url: str | None = None,
    password: str | None = None,
) -> uuid.UUID:
    """Create site, admin, grant, directory entry and audit trail.
    Returns the admin's user id; prints the password only if generated."""
    control_url = control_url or os.environ["GL_CONTROL_DB_URL"]
    base_url = base_url or os.environ["GL_TENANT_DB_URL"]

    generated = False
    if password is None:
        password = os.environ.get("GL_BOOTSTRAP_PASSWORD")
    if not password:
        password = secrets.token_urlsafe(18)
        generated = True

    registry = TenantRegistry(control_url)
    router = TenantRouter(registry, base_url)

    site_id = uuid.uuid4()
    user_id = uuid.uuid4()

    with router.bind(slug) as context:
        session = context.session
        audit = AuditService(AuditRepository(session))
        session.execute(
            sa.insert(sites).values(
                id=site_id, name=site_name, timezone=timezone_name
            )
        )
        session.execute(
            sa.insert(users).values(
                id=user_id,
                email=email.strip(),
                full_name=full_name,
                password_hash=PasswordHasher().hash(password),
            )
        )
        IdentityRepository(session).grant_role(
            user_id=user_id,
            role_name="site_admin",
            site_id=site_id,
            granted_by=user_id,
        )
        # The first admin is their own creator: there is no earlier
        # principal to attribute this to, and chk_audit_has_actor requires
        # a named actor for non-system actions.
        audit.write(
            action="site.created",
            entity_type="site",
            actor_user_id=user_id,
            entity_id=site_id,
            after_state={"name": site_name, "timezone": timezone_name},
        )
        audit.write(
            action="user.created",
            entity_type="user",
            actor_user_id=user_id,
            entity_id=user_id,
            after_state={
                "email": email.strip(),
                "full_name": full_name,
                "is_active": True,
            },
        )
        audit.write(
            action="user.role_granted",
            entity_type="user_role",
            actor_user_id=user_id,
            entity_key=f"{user_id}:site_admin:{site_id}",
            after_state={"role": "site_admin", "site_id": str(site_id)},
        )
        session.commit()  # one transaction for the whole tenant side

        tenant_id = context.tenant_id

    # Control side: login routing plus its lifecycle audit, one transaction.
    with psycopg.connect(psycopg_url(control_url)) as conn:
        conn.execute(
            "INSERT INTO user_directory (email_hash, tenant_id) VALUES (%s, %s)",
            (email_hash(email), str(tenant_id)),
        )
        conn.execute(
            """
            INSERT INTO control_audit_log (actor, action, tenant_id, after_state)
            VALUES (%s, 'tenant.admin_bootstrapped', %s,
                    jsonb_build_object('site', %s::text))
            """,
            (os.environ.get("USER", "system.bootstrap"), str(tenant_id), site_name),
        )
        conn.commit()

    if generated:
        # Printed exactly once, to stdout, never logged. The operator
        # hands it to the admin, who changes it at first login.
        print(f"generated admin password: {password}")
    return user_id


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m guardian_lens.api.bootstrap",
        description="Create the first site and admin user of a tenant.",
    )
    parser.add_argument("slug")
    parser.add_argument("email")
    parser.add_argument("full_name")
    parser.add_argument("--site-name", required=True)
    parser.add_argument("--timezone", required=True)
    args = parser.parse_args(argv)

    try:
        user_id = bootstrap(
            args.slug,
            args.email,
            args.full_name,
            site_name=args.site_name,
            timezone_name=args.timezone,
        )
    except (GuardianError, psycopg.Error, sa.exc.SQLAlchemyError) as exc:
        print(f"bootstrap failed: {exc}", file=sys.stderr)
        return 1
    print(f"bootstrapped admin {user_id} for tenant {args.slug}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
