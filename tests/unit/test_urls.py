"""Unit tests for URL handling. No database.

Alembic and SQLAlchemy want ``postgresql+psycopg://``; psycopg itself wants
``postgresql://``. Getting this wrong produces the worst kind of defect —
one that works in migrations and fails in the application, or vice versa.
"""

from __future__ import annotations

from urllib.parse import urlsplit

import pytest

from guardian_lens.db.urls import (
    admin_url,
    database_name,
    psycopg_url,
    sqlalchemy_url,
    tenant_database_name,
    tenant_url,
    with_database,
)
from guardian_lens.services.camera_discovery import anonymous_rtsp_url

BASE = "postgresql+psycopg://u:p@host:5432/gl_tenant_pilot"


def test_psycopg_url_strips_the_driver_suffix():
    assert psycopg_url(BASE) == "postgresql://u:p@host:5432/gl_tenant_pilot"


def test_psycopg_url_is_idempotent():
    once = psycopg_url(BASE)
    assert psycopg_url(once) == once


def test_sqlalchemy_url_adds_the_driver_suffix():
    assert sqlalchemy_url("postgresql://u:p@h/db") == "postgresql+psycopg://u:p@h/db"


def test_sqlalchemy_url_is_idempotent():
    assert sqlalchemy_url(BASE) == BASE


def test_round_trip_preserves_credentials_and_port():
    assert sqlalchemy_url(psycopg_url(BASE)) == BASE


def test_database_name():
    assert database_name(BASE) == "gl_tenant_pilot"


def test_with_database_replaces_only_the_path():
    assert with_database(BASE, "other") == "postgresql+psycopg://u:p@host:5432/other"


def test_admin_url_points_at_the_maintenance_database():
    """CREATE DATABASE cannot run from inside the database being created."""
    assert database_name(admin_url(BASE)) == "postgres"


def test_tenant_database_name_is_deterministic():
    """A hand-chosen database name is the first step towards a hand-built
    tenant, which is the schema-drift risk R-9 arriving on day one."""
    assert tenant_database_name("acme") == "gl_tenant_acme"
    assert tenant_database_name("acme-uk") == "gl_tenant_acme_uk"


def test_tenant_url_targets_the_derived_database():
    assert database_name(tenant_url(BASE, "globex")) == "gl_tenant_globex"


@pytest.mark.parametrize(
    "slug",
    [
        "",
        "has space",
        "semi;colon",
        'quote"',
        "../escape",
        "unicodeé",
        "ACME",
        "-leading-hyphen",
        "_leading_underscore",
    ],
)
def test_invalid_slugs_are_refused(slug):
    """The slug reaches a database name. It is validated before it gets
    anywhere near an identifier, not sanitised afterwards."""
    with pytest.raises(ValueError):
        tenant_database_name(slug)


def test_unusual_but_valid_slugs_are_accepted():
    """Safety comes from psycopg's sql.Identifier quoting, not from banning
    characters the schema itself permits. chk_tenants_slug_format allows
    hyphens anywhere after the first character, so this is a legitimate slug
    and the validator must not invent a stricter rule than the database's."""
    assert tenant_database_name("drop--table") == "gl_tenant_drop__table"


def test_validator_matches_the_database_constraint():
    """SLUG_PATTERN must stay identical to chk_tenants_slug_format in c0001.
    A validator looser than its constraint creates and migrates a database,
    then fails at registration, leaving an orphan."""
    from guardian_lens.db.urls import SLUG_PATTERN

    assert SLUG_PATTERN.pattern == r"^[a-z0-9][a-z0-9_-]*$"


def test_anonymous_rtsp_url_is_a_parseable_rtsp_uri():
    url = anonymous_rtsp_url("192.168.0.19", 554, "stream1")
    parts = urlsplit(url)
    assert parts.scheme == "rtsp"
    assert parts.hostname == "192.168.0.19"
    assert parts.port == 554
    assert parts.path == "/stream1"
    assert parts.username is None


def test_camera_rtsp_url_embeds_login_when_provided():
    from guardian_lens.services.camera_discovery import camera_rtsp_url

    url = camera_rtsp_url(
        "192.168.0.19", 554, "stream2", username="cam", password="secret"
    )
    parts = urlsplit(url)
    assert parts.hostname == "192.168.0.19"
    assert parts.path == "/stream2"
    assert parts.username == "cam"
    assert parts.password == "secret"
