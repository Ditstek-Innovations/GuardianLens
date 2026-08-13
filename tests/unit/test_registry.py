"""Invariants of the rule-to-enforcement registry. No database.

The registry is read by attestation, by the bypass suite and by migration
review. A defect here is a defect in all three at once.
"""

from __future__ import annotations

from collections import Counter

from guardian_lens.rules.registry import (
    ENFORCEMENT,
    ObjectKind,
    RuleStatus,
    for_rule,
    release_blocking,
)


def test_enforcement_names_are_unique():
    """Two entries with one name would make attestation report a phantom
    pass: the second is never independently verified."""
    duplicates = [n for n, c in Counter(e.name for e in ENFORCEMENT).items() if c > 1]
    assert not duplicates


def test_every_entry_states_its_intent():
    """DATABASE.md 4.3 question 7 asks which rules a migration affects and
    how each remains true. An entry with no stated intent cannot answer it,
    and 'why does this exist?' then gets decided by whoever is in a hurry."""
    assert all(len(e.intent.strip()) > 40 for e in ENFORCEMENT)


def test_only_active_rules_are_release_blocking():
    """A PROPOSED rule carries no force until ratified and must not be cited
    to block work — RULE_BOOK section 8, item 6."""
    for e in release_blocking():
        assert e.status in (RuleStatus.ACTIVE, RuleStatus.ACTIVE_CONDITIONAL)
    for e in ENFORCEMENT:
        if e.status is RuleStatus.PROPOSED:
            assert not e.is_release_blocking


def test_core_commitment_has_more_than_one_enforcement_point():
    """RULE_BOOK section 6: ABSOLUTE rules should have more than one
    enforcement point, so no single refactor can remove the guarantee."""
    assert len(for_rule("BR-004")) >= 2
    assert len(for_rule("BR-AU-01")) >= 2


def test_for_rule_returns_nothing_for_rules_with_no_database_point():
    """Five rules in the catalogue have no technical enforcement point at
    all and cannot acquire one. BR-M-01 is the one most likely to be broken
    and the cheapest to break: it will be broken by a slide, not a commit.

    This asserts the registry does not quietly claim otherwise."""
    assert for_rule("BR-M-01") == ()
    assert for_rule("BR-P-02") == ()


def test_every_kind_is_represented():
    kinds = {e.kind for e in ENFORCEMENT}
    assert kinds == {
        ObjectKind.CHECK,
        ObjectKind.UNIQUE,
        ObjectKind.TRIGGER,
        ObjectKind.INDEX,
    }


def test_rules_are_referenced_by_identifier_not_prose():
    for e in ENFORCEMENT:
        for rule in e.rules:
            assert rule.startswith(("BR-", "FR-", "NFR-")), rule
