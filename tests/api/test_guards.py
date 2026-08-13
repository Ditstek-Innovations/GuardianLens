"""The seven guards — 100% branch coverage, pass AND fail paths.

TRD 19.2: "Business-rule guards: each of the seven guards in §6.3, tested
for both pass and fail paths. 100% on business-rule guards — not
negotiable."
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest

from guardian_lens.core.errors import AlreadyDecidedError, AuditFieldError, ForbiddenFieldError
from guardian_lens.guards import (
    AuditWriteGuard,
    DefaultOffGuard,
    NoActionGuard,
    RejectionExclusionGuard,
    RetentionGuard,
    ReviewerAttributionGuard,
    VerificationGuard,
)
from guardian_lens.repositories.tables import events


# -- VerificationGuard — BR-004 ----------------------------------------------


@pytest.mark.active_rule("BR-004")
def test_verification_guard_passes_unverified():
    VerificationGuard.ensure_undecided("unverified", {})


@pytest.mark.active_rule("BR-004")
@pytest.mark.parametrize("status", ["accepted", "rejected", "corrected", "expired"])
def test_verification_guard_refuses_terminal_states(status):
    existing = {"status": status}
    with pytest.raises(AlreadyDecidedError) as exc:
        VerificationGuard.ensure_undecided(status, existing)
    assert exc.value.extra["existing_decision"] == existing


def test_verification_guard_status_mapping_is_total():
    assert VerificationGuard.decided_status_for("accept") == "accepted"
    assert VerificationGuard.decided_status_for("reject") == "rejected"
    assert VerificationGuard.decided_status_for("correct") == "corrected"
    with pytest.raises(KeyError):
        # No 'auto_accept', no 'escalate' — their absence is the design.
        VerificationGuard.decided_status_for("auto_accept")


# -- ReviewerAttributionGuard — BR-005, BR-S-01 ------------------------------


@pytest.mark.active_rule("BR-S-01")
def test_attribution_guard_passes_clean_body():
    ReviewerAttributionGuard.ensure_no_client_attribution(
        ["decision", "version", "rejection_reason"]
    )


@pytest.mark.active_rule("BR-S-01")
@pytest.mark.parametrize(
    "field", ["reviewer_id", "status", "decided_at", "decision_type"]
)
def test_attribution_guard_rejects_server_owned_fields(field):
    with pytest.raises(ForbiddenFieldError) as exc:
        ReviewerAttributionGuard.ensure_no_client_attribution(["decision", field])
    assert exc.value.field == field
    assert exc.value.http_status == 400  # the rule's 400, never a 422


@pytest.mark.active_rule("BR-005")
def test_attribution_guard_requires_a_reviewer():
    ReviewerAttributionGuard.ensure_attributed(uuid.uuid4())
    with pytest.raises(ValueError, match="BR-005"):
        ReviewerAttributionGuard.ensure_attributed(None)


# -- RejectionExclusionGuard — BR-R-01 ---------------------------------------


@pytest.mark.active_rule("BR-R-01")
def test_rejection_exclusion_predicate_content():
    """Query-builder inspection (TRD 6.3): the emitted SQL admits exactly
    accepted and corrected, and no other status can slip in."""
    predicate = RejectionExclusionGuard.verified_only(events.c.status)
    compiled = str(predicate.compile(compile_kwargs={"literal_binds": True}))
    assert "'accepted'" in compiled
    assert "'corrected'" in compiled
    for excluded in ("rejected", "unverified", "expired"):
        assert f"'{excluded}'" not in compiled


# -- DefaultOffGuard — BR-001, BR-C-02 ---------------------------------------


@pytest.mark.active_rule("BR-001")
def test_default_off_guard_accepts_inactive_creation():
    DefaultOffGuard.ensure_created_inactive(False)


@pytest.mark.active_rule("BR-001")
def test_default_off_guard_refuses_active_creation():
    with pytest.raises(ValueError, match="BR-001"):
        DefaultOffGuard.ensure_created_inactive(True)


@pytest.mark.proposed_rule("BR-C-02")
def test_default_off_guard_activation_attribution():
    now = datetime.now(timezone.utc)
    DefaultOffGuard.ensure_named_activator(uuid.uuid4(), now)
    with pytest.raises(ValueError, match="BR-C-02"):
        DefaultOffGuard.ensure_named_activator(None, now)
    with pytest.raises(ValueError, match="BR-C-02"):
        DefaultOffGuard.ensure_named_activator(uuid.uuid4(), None)


# -- AuditWriteGuard — BR-010, BR-AU-01 --------------------------------------


@pytest.mark.active_rule("BR-010")
def test_audit_guard_passes_allowlisted_state():
    state = {"status": "accepted", "version": 2}
    assert AuditWriteGuard.filter_state("event", state) == state


def test_audit_guard_passes_none_through():
    assert AuditWriteGuard.filter_state("event", None) is None


@pytest.mark.active_rule("BR-010")
@pytest.mark.parametrize(
    ("entity_type", "field"),
    [
        ("camera", "stream_url_encrypted"),
        ("camera", "stream_url"),
        ("user", "password_hash"),
        ("agent", "credential_hash"),
    ],
)
def test_audit_guard_refuses_forbidden_fields(entity_type, field):
    """DATABASE.md 10.4 — the audit log must never become the credential
    store's weakest replica."""
    with pytest.raises(AuditFieldError):
        AuditWriteGuard.filter_state(entity_type, {field: "anything"})


def test_audit_guard_refuses_unlisted_field():
    with pytest.raises(AuditFieldError):
        AuditWriteGuard.filter_state("event", {"surprise_field": 1})


def test_audit_guard_refuses_unknown_entity_type():
    with pytest.raises(AuditFieldError):
        AuditWriteGuard.filter_state("spaceship", {"name": "x"})


@pytest.mark.active_rule("BR-AU-01")
def test_audit_repository_is_structurally_insert_only():
    """TRD 6.4: no update or delete method exists AT ALL on the audit
    repository interface."""
    from guardian_lens.repositories.audit import AuditRepository

    exposed = {name for name in dir(AuditRepository) if not name.startswith("_")}
    assert exposed == {"insert", "page"}
    for verb in ("update", "delete", "truncate", "replace", "purge"):
        assert not any(verb in name.lower() for name in exposed)


# -- RetentionGuard — BR-009 [V1] --------------------------------------------


def test_retention_guard_is_an_honest_stub():
    """[V1]: both methods fail loudly instead of pretending retention is
    enforced (DATABASE.md 9.5 records the gap)."""
    with pytest.raises(NotImplementedError, match=r"\[V1\]"):
        RetentionGuard.ensure_deletion_recorded()
    with pytest.raises(NotImplementedError, match=r"\[V1\]"):
        RetentionGuard.ensure_within_policy()


# -- NoActionGuard — BR-003 --------------------------------------------------


@pytest.mark.active_rule("BR-003")
def test_no_action_guard_dependency_graph_is_clean(app):
    """With the whole application imported and wired, no consequence
    integration exists anywhere in the guardian_lens module graph."""
    NoActionGuard.assert_no_consequence_integrations()


@pytest.mark.active_rule("BR-003")
def test_no_action_guard_detects_a_planted_offender():
    """The fail path: the scanner actually catches what it exists for."""
    offenders = NoActionGuard.scan_module_names(
        [
            "guardian_lens.integrations.hr_webhook_client",
            "guardian_lens.services.ingest",
        ]
    )
    assert offenders == ["guardian_lens.integrations.hr_webhook_client"]

    import sys

    fake = "guardian_lens.integrations.disciplinary_export"
    sys.modules[fake] = type(sys)("disciplinary_export")
    try:
        with pytest.raises(AssertionError, match="BR-003"):
            NoActionGuard.assert_no_consequence_integrations()
    finally:
        del sys.modules[fake]


def test_no_action_guard_scan_passes_clean_names():
    assert NoActionGuard.scan_module_names(["guardian_lens.services.audit"]) == []
