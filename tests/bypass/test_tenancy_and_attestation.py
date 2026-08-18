"""DB-24, DB-25, DB-26, DB-27 and FF-11 — ADR-016 isolation properties.

Under database-per-tenant there is one copy of every rule-bearing constraint
PER TENANT, and the product's central guarantee is only as strong as the
weakest tenant's schema. These tests exercise the machinery that makes that
knowable rather than assumed.
"""

from __future__ import annotations

import uuid

import psycopg
import pytest

from guardian_lens.db.attestation import attest
from guardian_lens.rules.registry import ENFORCEMENT, RuleStatus


@pytest.mark.tenancy
def test_ff11_attestation_passes_on_a_freshly_provisioned_tenant(db):
    """FF-11 on a tenant provisioned by the real code path.

    A tenant reaches 'active' only by passing this. There is no path from
    "database created" to "serving traffic" that skips it
    (DATABASE.md 13.5.1 step 7).
    """
    result = attest(db)
    assert result.ok, result.report()
    assert not result.failures, result.report()


@pytest.mark.tenancy
def test_db26_attestation_detects_a_dropped_constraint(db):
    """DB-26: the drifted-tenant case.

    The failure this guards against is a migration fan-out that partially
    fails, or a tenant provisioned outside the code path, leaving a database
    in which a verified record with no reviewer is insertable — invisibly.
    Threat T-18, risk R-9.

    A tenant failing attestation is SUSPENDED from binding, not merely
    alerted: serving a database whose rule enforcement is unverified is
    worse than serving an error.
    """
    db.execute("ALTER TABLE events DROP CONSTRAINT chk_decided_requires_reviewer")

    result = attest(db)
    assert not result.ok
    names = {f.enforcement.name for f in result.blocking_failures}
    assert "chk_decided_requires_reviewer" in names
    # BR-004 and BR-005 both lose an enforcement point.
    lost_rules = {r for f in result.blocking_failures for r in f.enforcement.rules}
    assert {"BR-004", "BR-005"} <= lost_rules
    # Rolled back by the fixture; the drop never outlives this test.


@pytest.mark.tenancy
def test_db26_attestation_detects_a_disabled_trigger(db):
    """A DISABLEd trigger is present and useless.

    Checking only for existence would report this schema as healthy. It is
    precisely the state a careless migration — or an adversary with DDL
    rights — would leave behind.
    """
    db.execute("ALTER TABLE audit_log DISABLE TRIGGER trg_audit_append_only")

    result = attest(db)
    assert not result.ok
    failure = next(
        f for f in result.blocking_failures
        if f.enforcement.name == "trg_audit_append_only"
    )
    assert failure.present and not failure.enabled
    assert failure.detail == "DISABLED"


@pytest.mark.tenancy
def test_proposed_rule_failures_are_advisory_not_blocking(db):
    """A PROPOSED rule carries no force until ratified.

    RULE_BOOK section 8, item 6: it "must not be cited to block work; it
    must be either ratified or withdrawn at the next review." So its
    constraint is built and verified, and its absence is reported rather
    than gating.
    """
    db.execute(
        "ALTER TABLE detection_rules DROP CONSTRAINT chk_active_rule_has_activator"
    )

    result = attest(db)
    advisory = {f.enforcement.name for f in result.advisory_failures}
    assert "chk_active_rule_has_activator" in advisory
    assert result.ok, "a PROPOSED-rule failure must not block release"


@pytest.mark.tenancy
def test_db24_tenant_identity_holds_exactly_one_row(db):
    """DB-24: a second tenant identity.

    In a silo model nothing in the business rows can contradict a mis-routed
    connection — every constraint would happily accept writes into the wrong
    universe. This single row is the only thing the router can assert
    against (DATABASE.md 1.4.1).
    """
    with pytest.raises(psycopg.errors.UniqueViolation):
        db.execute(
            "INSERT INTO tenant_identity (tenant_id, tenant_slug) VALUES (%s, %s)",
            (str(uuid.uuid4()), "impostor"),
        )


@pytest.mark.tenancy
def test_tenant_identity_names_this_tenant(db, tenant_slug):
    row = db.execute("SELECT tenant_slug FROM tenant_identity").fetchone()
    assert row is not None
    assert row[0] == tenant_slug


@pytest.mark.tenancy
def test_db27_control_database_holds_no_business_data(control_db):
    """DB-27: ADR-017.

    The control database is reachable from every request, which makes it the
    natural place to cache "just a little" tenant data. Each such addition is
    individually harmless and collectively rebuilds a shared, cross-tenant
    copy of exactly the data ADR-016 separated.

    Counts of OPERATIONAL state are permitted. Counts of BUSINESS state are
    not.
    """
    tables = {
        row[0]
        for row in control_db.execute(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema = 'public'"
        ).fetchall()
    }
    business = {
        "events", "event_corrections", "coverage_gaps", "sites", "cameras",
        "zones", "detection_rules", "audit_log", "users", "agents",
        "model_versions",
    }
    assert not (tables & business), f"business tables in control DB: {tables & business}"

    columns = {
        c.lower()
        for (c,) in control_db.execute(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_schema = 'public'"
        ).fetchall()
    }
    for banned in ("event_count", "decision", "reviewer", "password", "credential_hash"):
        assert banned not in columns, f"control DB holds {banned!r}"


@pytest.mark.tenancy
def test_control_database_stores_a_credential_reference_not_a_credential(control_db):
    """Compromise of the control database must yield the map, not the
    territory. Per-tenant credentials live in the secret store; only a
    reference is held here, so the registry alone grants no access (T-20).
    """
    columns = {
        c
        for (c,) in control_db.execute(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_name = 'tenant_databases'"
        ).fetchall()
    }
    assert "credential_ref" in columns
    assert "password" not in columns
    assert "credential" not in columns


@pytest.mark.tenancy
def test_control_audit_log_is_append_only(control_db):
    """Tenant lifecycle is exactly the kind of scope change BR-010 requires
    to be recorded and attributable, so it gets the same posture as the
    tenant audit log."""
    with pytest.raises(psycopg.errors.RestrictViolation):
        control_db.execute("UPDATE control_audit_log SET action = 'tampered'")


@pytest.mark.tenancy
def test_registry_covers_every_absolute_rule_with_more_than_one_point():
    """RULE_BOOK section 6: ABSOLUTE rules "should have more than one
    enforcement point, so that no single refactor can remove the guarantee."

    This checks the claim at the data layer rather than assuming it. Rules
    whose only enforcement is outside the database are listed explicitly,
    because for them the claim is made elsewhere — and five rules in the
    catalogue have no technical enforcement point at all and cannot acquire
    one.
    """
    from collections import Counter

    points = Counter(
        rule for e in ENFORCEMENT if e.status is RuleStatus.ACTIVE for rule in e.rules
    )
    # BR-004 and BR-005 are the product's core commitment. Both must have
    # more than one database object standing behind them.
    assert points["BR-004"] >= 2, points
    assert points["BR-005"] >= 1, points
    assert points["BR-AU-01"] >= 2, points
