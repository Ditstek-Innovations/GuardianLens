"""DB-9, DB-11, DB-12, DB-13, DB-14, DB-19 — schema invariants.

These are not numbered business rules. They are the invariants the rules
depend on: a wrong site_id misfiles an event into another site's reports; a
rule active with no named activator leaves gate G2 evidence in audit_log
alone; a model deployed with no approver bypasses gate G1 entirely.
"""

from __future__ import annotations

import uuid

import psycopg
import pytest

from tests.conftest import insert_event


@pytest.mark.coherence
def test_db9_event_site_id_must_match_its_camera(db, seed):
    """DB-9: the trigger TRD 8.3 promises and never defines.

    Denormalising site_id onto events removes a join on the hottest
    reporting path. Left unenforced it is an invariant nothing maintains,
    and a wrong value silently misfiles an event into another site's
    reports — a cross-site data-integrity failure under ADR-012.
    """
    other_site = db.execute(
        "INSERT INTO sites (name, timezone) VALUES ('Other', 'UTC') RETURNING id"
    ).fetchone()[0]

    with pytest.raises(psycopg.errors.CheckViolation) as exc:
        insert_event(db, seed, site_id=other_site)
    assert "does not match" in str(exc.value)


@pytest.mark.coherence
def test_site_id_is_derived_when_omitted(db, seed):
    """Derive when absent, reject when contradictory.

    Silently overwriting a supplied-but-wrong value would hide a caller
    defect; rejecting it surfaces one. Omission is not a defect, so it is
    filled in.
    """
    event_id = uuid.uuid4()
    # evidence_state is stated explicitly. It defaults to 'present', and
    # chk_evidence_state_coherent then requires an evidence_ref — so a caller
    # cannot quietly leave the provenance of the frame undeclared. That is the
    # constraint doing its job, and it is why this INSERT names the column.
    db.execute(
        """
        INSERT INTO events (id, event_id, site_id, camera_id, rule_snapshot,
                            agent_id, model_version_id, confidence, occurred_at,
                            evidence_state)
        VALUES (%s, %s, NULL, %s, '{}', %s, %s, 0.9, now(), 'none')
        """,
        (event_id, uuid.uuid4(), seed["camera"], seed["agent"], seed["model"]),
    )
    site_id = db.execute(
        "SELECT site_id FROM events WHERE id = %s", (event_id,)
    ).fetchone()[0]
    assert site_id == seed["site"]


@pytest.mark.proposed_rule("BR-C-02")
def test_db11_active_rule_must_name_its_activator(db, seed):
    """DB-11: activate a rule with no named activator.

    BR-C-02: there is no path by which a detection rule becomes active
    without a named user having activated it. TRD 9.4 records only
    created_by, so the activation fact lives solely in audit_log — a real
    trail, but one where a defect that skips the audit write leaves
    activation entirely unattributed. Gate G2 evidence. AMD-DB-07.
    """
    rule_id = db.execute(
        """
        INSERT INTO detection_rules
            (zone_id, rule_type, confidence_threshold, debounce_seconds,
             human_readable, created_by)
        VALUES (%s, 'ppe_helmet', 0.5, 30, 'test', %s)
        RETURNING id
        """,
        (seed["zone"], seed["user"]),
    ).fetchone()[0]

    with pytest.raises(psycopg.errors.CheckViolation) as exc:
        db.execute(
            "UPDATE detection_rules SET is_active = TRUE WHERE id = %s", (rule_id,)
        )
    assert "chk_active_rule_has_activator" in str(exc.value)


@pytest.mark.active_rule("BR-001")
def test_a_new_rule_is_inactive_by_default(db, seed):
    """BR-001, ABSOLUTE — nothing is monitored by default.

    The rule lives in a column default. A freshly created rule generates no
    candidate events until a named user deliberately enables it.
    """
    is_active = db.execute(
        """
        INSERT INTO detection_rules
            (zone_id, rule_type, confidence_threshold, debounce_seconds,
             human_readable, created_by)
        VALUES (%s, 'ppe_helmet', 0.5, 30, 'test', %s)
        RETURNING is_active
        """,
        (seed["zone"], seed["user"]),
    ).fetchone()[0]
    assert is_active is False


@pytest.mark.proposed_rule("BR-D-01")
def test_db12_guardian_lens_event_requires_a_model_version(db, seed):
    """DB-12: a Guardian Lens event with no model version.

    Every detection carries the model version that produced it. If a version
    is later found defective the affected events must be identifiable
    exactly, and deriving the version from a deployment timeline is an
    approximation. An approximation is not evidence.
    """
    with pytest.raises(psycopg.errors.CheckViolation) as exc:
        insert_event(db, seed, source="guardian_lens", model_version_id=None)
    assert "chk_model_version_required" in str(exc.value)


@pytest.mark.coherence
def test_nvr_event_may_omit_the_model_version(db, seed):
    """The null is permitted exactly where legitimate. FR-032, FR-013."""
    event_id = insert_event(
        db, seed, source="nvr", model_version_id=None, confidence=None
    )
    source = db.execute(
        "SELECT source FROM events WHERE id = %s", (event_id,)
    ).fetchone()[0]
    assert source == "nvr"


@pytest.mark.coherence
def test_db13_model_cannot_deploy_without_a_recorded_approver(db):
    """DB-13: gate G1 as a constraint.

    It cannot verify that a model card is good — nothing in a database can.
    It makes deploying a model version with NO recorded approver at all
    impossible, which is a different and achievable claim. AMD-DB-08.
    """
    model_id = db.execute(
        "INSERT INTO model_versions (version, artefact_hash, classes) "
        "VALUES ('9.9.9', 'sha256:x', '[]') RETURNING id"
    ).fetchone()[0]

    with pytest.raises(psycopg.errors.CheckViolation) as exc:
        db.execute(
            "UPDATE model_versions SET deployed_at = now() WHERE id = %s", (model_id,)
        )
    assert "chk_model_deployed_requires_approval" in str(exc.value)


@pytest.mark.coherence
def test_db19_two_open_gaps_for_one_camera_are_rejected(db, seed):
    """DB-19: double-counted unavailability.

    Two simultaneously open gaps for one agent, camera and reason would
    double-count in any coverage report — and coverage reporting exists so
    that "nothing happened" and "we were not watching" stay
    distinguishable. AMD-DB-15.
    """
    for _ in range(1):
        db.execute(
            """
            INSERT INTO coverage_gaps (id, site_id, camera_id, agent_id,
                                       started_at, reason, recorded_by)
            VALUES (%s, %s, %s, %s, now(), 'stream_lost', 'agent')
            """,
            (uuid.uuid4(), seed["site"], seed["camera"], seed["agent"]),
        )

    with pytest.raises(psycopg.errors.UniqueViolation) as exc:
        db.execute(
            """
            INSERT INTO coverage_gaps (id, site_id, camera_id, agent_id,
                                       started_at, reason, recorded_by)
            VALUES (%s, %s, %s, %s, now(), 'stream_lost', 'agent')
            """,
            (uuid.uuid4(), seed["site"], seed["camera"], seed["agent"]),
        )
    assert "uq_coverage_gaps_open" in str(exc.value)


@pytest.mark.coherence
def test_agent_down_gap_needs_no_camera(db, seed):
    """A dead agent has no camera to attribute the gap to, and no ability to
    write the row. TRD 9.7 makes camera_id NOT NULL while listing agent_down
    as a reason, which cannot both hold. AMD-DB-10.
    """
    db.execute(
        """
        INSERT INTO coverage_gaps (id, site_id, camera_id, agent_id,
                                   started_at, reason, recorded_by)
        VALUES (%s, %s, NULL, %s, now(), 'agent_down', 'control_plane')
        """,
        (uuid.uuid4(), seed["site"], seed["agent"]),
    )
    recorded_by = db.execute(
        "SELECT recorded_by FROM coverage_gaps WHERE reason = 'agent_down'"
    ).fetchone()[0]
    assert recorded_by == "control_plane"


@pytest.mark.coherence
def test_a_user_without_any_credential_cannot_exist(db):
    with pytest.raises(psycopg.errors.CheckViolation) as exc:
        db.execute(
            "INSERT INTO users (email, full_name) VALUES ('x@example.test', 'X')"
        )
    assert "chk_users_has_credential" in str(exc.value)


@pytest.mark.coherence
def test_deleting_a_camera_with_events_is_refused(db, seed):
    """ON DELETE RESTRICT, not CASCADE. DATABASE.md 3.2.

    CASCADE here would let a configuration action silently delete verified
    records (BR-007) and their attribution (BR-AU-02). No ON DELETE
    behaviour is stated anywhere in TRD 9 — AMD-DB-06.
    """
    insert_event(db, seed)
    # PostgreSQL 16 reports ON DELETE RESTRICT as ForeignKeyViolation
    # (23503); PostgreSQL 18 reports RestrictViolation (23001). The refusal
    # is identical — only the error class differs across server versions.
    with pytest.raises(
        (psycopg.errors.ForeignKeyViolation, psycopg.errors.RestrictViolation)
    ):
        db.execute("DELETE FROM cameras WHERE id = %s", (seed["camera"],))


@pytest.mark.coherence
def test_deleting_a_reviewer_with_decisions_is_refused(db, seed):
    """A reviewer can never be deleted while attributed to a record.
    Deactivate instead. The people the system records by name are the people
    accountable for its decisions (DATABASE.md 8.3).
    """
    insert_event(
        db, seed,
        status="accepted",
        reviewer_id=seed["user"],
        decided_at="2026-08-12T10:00:00+00:00",
        decision_type="accept",
    )
    # PostgreSQL 16 reports ON DELETE RESTRICT as ForeignKeyViolation
    # (23503); PostgreSQL 18 reports RestrictViolation (23001). The refusal
    # is identical — only the error class differs across server versions.
    with pytest.raises(
        (psycopg.errors.ForeignKeyViolation, psycopg.errors.RestrictViolation)
    ):
        db.execute("DELETE FROM users WHERE id = %s", (seed["user"],))
