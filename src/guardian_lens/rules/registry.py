"""Rule-to-enforcement registry.

One machine-readable map from a business rule to the database objects that
make it true, derived from RULE_BOOK.md section 6 and DATABASE.md section 6.6.

Three consumers, one source:

  * ``guardian_lens.db.attestation``  — FF-11 verifies every entry exists and
    is enabled in every active tenant database, continuously in production.
  * ``tests/bypass``                  — the bypass suite (TRD 19.4) attempts to
    violate each rule and asserts the database refuses.
  * migration review                  — DATABASE.md section 4.3 question 7 asks
    which rules a migration affects. This is the lookup table for that answer.

Business Rules Manifesto article 4.5: a rule is distinct from any enforcement
defined for it. ``rule`` and ``name`` are therefore separate fields. A rule
whose enforcement moves from one object to another has not changed; a rule
whose statement changes is a different rule requiring ratification under
GOVERNANCE.md section 8.4.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

__all__ = [
    "ObjectKind",
    "RuleStatus",
    "Enforcement",
    "ENFORCEMENT",
    "release_blocking",
    "for_rule",
]


class ObjectKind(str, Enum):
    """What kind of database object carries the enforcement."""

    CHECK = "check"
    UNIQUE = "unique"
    TRIGGER = "trigger"
    INDEX = "index"


class RuleStatus(str, Enum):
    """Ratification status, per RULE_BOOK.md section 10.

    PROPOSED rules carry no force until ratified (RULE_BOOK.md section 8,
    item 6) and must not be cited to block work. Their constraints are built
    because DATABASE.md specifies them, but they are reported separately so
    nothing implies they are ratified.
    """

    ACTIVE = "active"
    ACTIVE_CONDITIONAL = "active_conditional"
    PROPOSED = "proposed"
    #: Not a numbered rule — a schema invariant, a governance gate, or an
    #: architectural property. Still verified; simply not rule-derived.
    COHERENCE = "coherence"


@dataclass(frozen=True, slots=True)
class Enforcement:
    """One database object that makes one or more rules true."""

    name: str
    kind: ObjectKind
    table: str
    rules: tuple[str, ...]
    status: RuleStatus
    #: Why this object exists, in one line. Read by whoever is deciding
    #: whether a migration may drop it. The answer is almost always no.
    intent: str
    #: Scope tag from TRD's convention.
    scope: str = "[MVP]"

    @property
    def is_release_blocking(self) -> bool:
        """A failure here blocks release regardless of feature completeness.

        TRD 19.4: "If it passes, the product's core commitments hold. If it
        fails, the product is not shippable regardless of feature
        completeness." That statement is about ABSOLUTE rules that are
        ACTIVE. PROPOSED rules are reported, not enforced as gates.
        """
        return self.status in (RuleStatus.ACTIVE, RuleStatus.ACTIVE_CONDITIONAL)


# --------------------------------------------------------------------------
# The registry.
#
# Ordered by the section of DATABASE.md that specifies each object, so a
# reviewer can read the two side by side.
# --------------------------------------------------------------------------

ENFORCEMENT: tuple[Enforcement, ...] = (
    # -- DATABASE.md 6.1 — the verification constraints -------------------
    Enforcement(
        name="chk_decided_requires_reviewer",
        kind=ObjectKind.CHECK,
        table="events",
        rules=("BR-004", "BR-005"),
        status=RuleStatus.ACTIVE,
        intent=(
            "Reads in both directions. A decided row MUST carry its reviewer "
            "(BR-005); an unverified row MUST NOT (BR-004, forbidding "
            "pre-filled attribution). The fourth and least removable layer of "
            "the defence-in-depth pattern in ARCHITECTURE.md 4.2."
        ),
    ),
    Enforcement(
        name="chk_rejection_has_reason",
        kind=ObjectKind.CHECK,
        table="events",
        rules=("FR-043",),
        status=RuleStatus.COHERENCE,
        intent="A rejection without a stated reason is not reviewable.",
    ),
    Enforcement(
        name="chk_status_valid",
        kind=ObjectKind.CHECK,
        table="events",
        rules=("BR-004",),
        status=RuleStatus.ACTIVE,
        intent=(
            "The allowed status set, spelled out. DATABASE.md 6.5 chooses "
            "VARCHAR + CHECK over a native ENUM precisely so that adding a "
            "value such as 'auto_accepted' appears in a migration diff as an "
            "unmistakable rewrite of a named constraint."
        ),
    ),
    Enforcement(
        name="chk_decision_type_valid",
        kind=ObjectKind.CHECK,
        table="events",
        rules=("BR-004",),
        status=RuleStatus.ACTIVE,
        intent="accept | reject | correct. No fourth disposition exists.",
    ),
    # -- DATABASE.md 6.4 — conditional presence ---------------------------
    Enforcement(
        name="chk_model_version_required",
        kind=ObjectKind.CHECK,
        table="events",
        rules=("BR-D-01",),
        status=RuleStatus.PROPOSED,
        intent=(
            "Every detection carries the model version that produced it. The "
            "null is permitted exactly where legitimate (NVR-sourced events) "
            "and nowhere else, so no Guardian Lens event can have "
            "unreconstructible provenance."
        ),
    ),
    Enforcement(
        name="chk_confidence_required",
        kind=ObjectKind.CHECK,
        table="events",
        rules=("BR-D-01",),
        status=RuleStatus.PROPOSED,
        intent="Same null-where-legitimate discipline, for confidence.",
    ),
    Enforcement(
        name="chk_source_valid",
        kind=ObjectKind.CHECK,
        table="events",
        rules=("FR-032",),
        status=RuleStatus.COHERENCE,
        intent="guardian_lens | nvr. Provenance is retained, never inferred.",
    ),
    Enforcement(
        name="chk_evidence_state_coherent",
        kind=ObjectKind.CHECK,
        table="events",
        rules=(),
        status=RuleStatus.COHERENCE,
        intent=(
            "Distinguishes 'never captured' from 'deleted per retention' from "
            "'storage failed'. Without it an inspector cannot tell whether a "
            "reviewer saw a frame — DATABASE.md 5.5."
        ),
    ),
    Enforcement(
        name="chk_active_rule_has_activator",
        kind=ObjectKind.CHECK,
        table="detection_rules",
        rules=("BR-C-02", "BR-001"),
        status=RuleStatus.PROPOSED,
        intent=(
            "There is no path by which a rule becomes active without a named "
            "user having activated it. Puts the answer in the row rather than "
            "requiring reconstruction from audit_log — gate G2 evidence."
        ),
    ),
    Enforcement(
        name="chk_rule_requires_zone",
        kind=ObjectKind.CHECK,
        table="detection_rules",
        rules=(),
        status=RuleStatus.COHERENCE,
        intent=(
            "Redundant given NOT NULL plus the foreign key. Retained as a "
            "named artefact because TRD 8.4 and the review checklists refer "
            "to it by name, and a checklist that cannot find its object "
            "reports a false negative."
        ),
    ),
    Enforcement(
        name="chk_model_deployed_requires_approval",
        kind=ObjectKind.CHECK,
        table="model_versions",
        rules=(),
        status=RuleStatus.COHERENCE,
        intent=(
            "Gate G1 as a constraint. It cannot verify that a model card is "
            "good — nothing in a database can — but it makes deploying a "
            "model version with no recorded approver impossible."
        ),
    ),
    Enforcement(
        name="chk_users_has_credential",
        kind=ObjectKind.CHECK,
        table="users",
        rules=(),
        status=RuleStatus.COHERENCE,
        intent="A user with no authentication path cannot exist.",
    ),
    Enforcement(
        name="chk_audit_has_actor",
        kind=ObjectKind.CHECK,
        table="audit_log",
        rules=("BR-010",),
        status=RuleStatus.ACTIVE,
        intent=(
            "Exactly one actor, or an explicit system action. An audit entry "
            "can never have an unexplained absence of actor."
        ),
    ),
    Enforcement(
        name="chk_tenant_identity_singleton",
        kind=ObjectKind.CHECK,
        table="tenant_identity",
        rules=(),
        status=RuleStatus.COHERENCE,
        intent=(
            "Exactly one row. Read by the Tenant Router before any query "
            "executes; in a silo model nothing in the data itself can "
            "contradict a mis-routed connection — ADR-016, DATABASE.md 1.4.1."
        ),
    ),
    # -- DATABASE.md 6.6 — uniqueness -------------------------------------
    Enforcement(
        name="uq_events_event_id",
        kind=ObjectKind.UNIQUE,
        table="events",
        rules=(),
        status=RuleStatus.COHERENCE,
        intent=(
            "Client-generated idempotency key. At-least-once delivery from "
            "the edge outbox becomes exactly-once effect at ingest. Becomes "
            "impossible once events is partitioned — see DATABASE.md 3.5."
        ),
    ),
    Enforcement(
        name="uq_users_email",
        kind=ObjectKind.UNIQUE,
        table="users",
        rules=(),
        status=RuleStatus.COHERENCE,
        intent="One account per address, case-insensitively (CITEXT).",
    ),
    Enforcement(
        name="uq_coverage_gaps_open",
        kind=ObjectKind.INDEX,
        table="coverage_gaps",
        rules=("BR-W-01",),
        status=RuleStatus.PROPOSED,
        intent=(
            "Partial unique index. Prevents two simultaneously open gaps for "
            "one agent, camera and reason, which would double-count "
            "unavailability in coverage reporting."
        ),
    ),
    # -- DATABASE.md 6.2, 6.3, 10.1 — triggers ----------------------------
    Enforcement(
        name="trg_events_immutable_decision",
        kind=ObjectKind.TRIGGER,
        table="events",
        rules=("BR-AU-02", "BR-V-01"),
        status=RuleStatus.ACTIVE,
        intent=(
            "Reviewer identity, decision timestamp and decision type are "
            "immutable once set, and a terminal event may never return to "
            "unverified. A reviewer error is addressed by a new correcting "
            "record; an audit trail that can be edited is not an audit trail."
        ),
    ),
    Enforcement(
        name="trg_events_site_consistency",
        kind=ObjectKind.TRIGGER,
        table="events",
        rules=(),
        status=RuleStatus.COHERENCE,
        intent=(
            "TRD 8.3 promises this trigger and never defines it. Derives "
            "site_id when absent, rejects it when it contradicts the camera. "
            "A wrong site_id misfiles an event into another site's reports."
        ),
    ),
    Enforcement(
        name="trg_audit_append_only",
        kind=ObjectKind.TRIGGER,
        table="audit_log",
        rules=("BR-AU-01",),
        status=RuleStatus.ACTIVE,
        intent="UPDATE and DELETE on the audit log are rejected, whatever the caller.",
    ),
    Enforcement(
        name="trg_audit_no_truncate",
        kind=ObjectKind.TRIGGER,
        table="audit_log",
        rules=("BR-AU-01",),
        status=RuleStatus.ACTIVE,
        intent=(
            "A row-level trigger does NOT fire on TRUNCATE. Without this "
            "statement-level trigger, TRUNCATE audit_log succeeds silently "
            "while the bypass suite's UPDATE and DELETE cases still pass — "
            "DATABASE.md 10.1, amendment AMD-DB-16."
        ),
    ),
    Enforcement(
        name="trg_detection_rules_touch_updated_at",
        kind=ObjectKind.TRIGGER,
        table="detection_rules",
        rules=(),
        status=RuleStatus.COHERENCE,
        intent="updated_at is set by the database, not trusted from the caller.",
    ),
    # -- migration 0011 — self-service password reset (CS-AU-10 v1.4) ------
    Enforcement(
        name="uq_password_reset_tokens_hash",
        kind=ObjectKind.UNIQUE,
        table="password_reset_tokens",
        rules=(),
        status=RuleStatus.COHERENCE,
        intent=(
            "One stored hash, one token. A duplicated hash would let a "
            "second token satisfy a lookup meant for exactly one."
        ),
    ),
    Enforcement(
        name="chk_reset_hash_length",
        kind=ObjectKind.CHECK,
        table="password_reset_tokens",
        rules=(),
        status=RuleStatus.COHERENCE,
        intent=(
            "32 bytes = SHA-256. A row of any other length means plaintext "
            "or a truncated digest reached the store — either is a defect."
        ),
    ),
    Enforcement(
        name="chk_reset_expiry_ordered",
        kind=ObjectKind.CHECK,
        table="password_reset_tokens",
        rules=(),
        status=RuleStatus.COHERENCE,
        intent="A token that expires before it exists is a clock or code defect.",
    ),
    Enforcement(
        name="chk_detection_rules_detection_class_length",
        kind=ObjectKind.CHECK,
        table="detection_rules",
        rules=(),
        status=RuleStatus.COHERENCE,
        intent=(
            "An empty detection_class would be silently unreachable — no "
            "model output could ever equal it, so the rule could never "
            "fire and nothing would say why."
        ),
    ),
    # -- DATABASE.md 7.2 — indexes serving named queries -------------------
    Enforcement(
        name="idx_events_queue",
        kind=ObjectKind.INDEX,
        table="events",
        rules=(),
        status=RuleStatus.COHERENCE,
        intent=(
            "Q-1, the review queue — the hottest read path and the one a "
            "reviewer feels. Partial on status='unverified', so its size "
            "tracks the undisposed backlog rather than total history."
        ),
    ),
    Enforcement(
        name="idx_events_site_occurred",
        kind=ObjectKind.INDEX,
        table="events",
        rules=("BR-R-01",),
        status=RuleStatus.ACTIVE,
        intent=(
            "Q-3, reporting. Partial on the verified statuses, because every "
            "report query filters them at the repository layer anyway."
        ),
    ),
    Enforcement(
        name="idx_audit_entity_time",
        kind=ObjectKind.INDEX,
        table="audit_log",
        rules=("BR-AU-01",),
        status=RuleStatus.ACTIVE,
        intent="Q-7. Audit retrieval must never be the slow path.",
    ),
)


def release_blocking() -> tuple[Enforcement, ...]:
    """Enforcement objects whose absence blocks release."""
    return tuple(e for e in ENFORCEMENT if e.is_release_blocking)


def for_rule(rule_id: str) -> tuple[Enforcement, ...]:
    """Every database object enforcing a given rule.

    RULE_BOOK.md section 6: ABSOLUTE rules should have more than one
    enforcement point, so that no single refactor can remove the guarantee.
    This is how you check that claim rather than assuming it.
    """
    return tuple(e for e in ENFORCEMENT if rule_id in e.rules)
