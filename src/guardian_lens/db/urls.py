"""URL helpers.

Alembic and SQLAlchemy want ``postgresql+psycopg://``; psycopg itself wants
``postgresql://``. One conversion, in one place, so the difference never
becomes a source of "works in migrations, fails in tests".
"""

from __future__ import annotations

import re
from urllib.parse import urlsplit, urlunsplit

__all__ = [
    "psycopg_url",
    "sqlalchemy_url",
    "database_name",
    "with_database",
    "admin_url",
    "tenant_database_name",
    "tenant_url",
]

_DRIVER_PREFIX = "postgresql+psycopg"

#: Must stay identical to chk_tenants_slug_format in migration c0001.
#: A validator looser than its constraint creates the database, migrates it,
#: then fails at registration — leaving an orphan nothing owns.
SLUG_PATTERN = re.compile(r"^[a-z0-9][a-z0-9_-]*$")


def psycopg_url(url: str) -> str:
    """Strip the SQLAlchemy driver suffix for direct psycopg use."""
    if url.startswith(_DRIVER_PREFIX):
        return "postgresql" + url[len(_DRIVER_PREFIX) :]
    return url


def sqlalchemy_url(url: str) -> str:
    """Add the driver suffix for SQLAlchemy and Alembic."""
    if url.startswith(_DRIVER_PREFIX):
        return url
    if url.startswith("postgresql://"):
        return _DRIVER_PREFIX + url[len("postgresql") :]
    return url


def database_name(url: str) -> str:
    return urlsplit(psycopg_url(url)).path.lstrip("/")


def with_database(url: str, name: str) -> str:
    parts = urlsplit(sqlalchemy_url(url))
    return urlunsplit(parts._replace(path=f"/{name}"))


def admin_url(url: str) -> str:
    """A URL pointing at the maintenance database.

    CREATE DATABASE cannot run from inside the database being created, so
    provisioning connects to ``postgres`` first.
    """
    return with_database(url, "postgres")


def tenant_database_name(slug: str) -> str:
    """Derive a tenant database name from its slug.

    Deterministic on purpose: DATABASE.md 13.5.1 makes provisioning a code
    path, never a runbook, and a hand-chosen database name is the first step
    towards a hand-built tenant.
    """
    if not SLUG_PATTERN.fullmatch(slug):
        raise ValueError(
            f"invalid tenant slug {slug!r}: must match {SLUG_PATTERN.pattern} "
            f"(same rule as chk_tenants_slug_format in migration c0001)"
        )
    return f"gl_tenant_{slug.replace('-', '_')}"


def tenant_url(base_url: str, slug: str) -> str:
    return with_database(base_url, tenant_database_name(slug))
