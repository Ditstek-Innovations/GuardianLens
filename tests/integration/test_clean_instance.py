"""FF-8 — the clean-instance test, on its own freshly provisioned tenant.

BR-001 is ABSOLUTE: nothing is monitored by default, and a newly deployed
system generates no candidate events. Not "generates few" — none, because
there is nothing configured to generate them from.

This gets a dedicated tenant deliberately. Asserting emptiness inside a
shared database would pass or fail depending on what other tests had done,
and a flaky clean-instance test is worse than none: it teaches the team to
ignore the one check standing behind an ABSOLUTE rule.
"""

from __future__ import annotations

import os
import uuid
from collections.abc import Iterator

import psycopg
import pytest

from guardian_lens.db.provisioning import deprovision, provision
from guardian_lens.db.urls import psycopg_url, tenant_url


@pytest.fixture
def fresh_tenant(control_url: str) -> Iterator[psycopg.Connection]:
    base = os.environ["GL_TENANT_DB_URL"]
    slug = f"clean_{uuid.uuid4().hex[:8]}"
    provision(slug, "Clean instance", base_url=base, control_url=control_url)
    conn = psycopg.connect(psycopg_url(tenant_url(base, slug)))
    try:
        yield conn
    finally:
        conn.close()
        deprovision(slug, base_url=base, control_url=control_url)


@pytest.mark.active_rule("BR-001")
def test_ff8_a_fresh_tenant_has_no_configuration_and_no_events(fresh_tenant):
    counts = fresh_tenant.execute(
        """
        SELECT (SELECT count(*) FROM sites),
               (SELECT count(*) FROM cameras),
               (SELECT count(*) FROM zones),
               (SELECT count(*) FROM detection_rules),
               (SELECT count(*) FROM detection_rules WHERE is_active),
               (SELECT count(*) FROM events),
               (SELECT count(*) FROM agents)
        """
    ).fetchone()
    assert counts == (0, 0, 0, 0, 0, 0, 0)


@pytest.mark.active_rule("BR-001")
def test_ff8_reference_data_is_seeded_but_configuration_is_not(fresh_tenant):
    """Roles are reference data and are seeded with fixed IDs so grants stay
    comparable across tenants. Detection rules are configuration and are
    never seeded — a seeded rule would violate BR-001 outright."""
    assert fresh_tenant.execute("SELECT count(*) FROM roles").fetchone()[0] == 4
    assert fresh_tenant.execute(
        "SELECT count(*) FROM detection_rules"
    ).fetchone()[0] == 0


@pytest.mark.tenancy
def test_a_fresh_tenant_knows_which_tenant_it_is(fresh_tenant):
    row = fresh_tenant.execute(
        "SELECT tenant_id, tenant_slug FROM tenant_identity"
    ).fetchone()
    assert row is not None and row[1].startswith("clean_")
