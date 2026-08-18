"""VerificationGuard — BR-004: no record without human verification.

Only an unverified event may enter human verification, and only a decision
carrying a named reviewer may leave it. There is no timer, no confidence
value and no automated path out of 'unverified' (TRD 11.1) — so this guard
has no branch for one.
"""

from __future__ import annotations

from typing import Any

from guardian_lens.core.errors import AlreadyDecidedError

UNVERIFIED = "unverified"


class VerificationGuard:
    """Gate on the single transition out of 'unverified'."""

    @staticmethod
    def ensure_undecided(status: str, existing_decision: dict[str, Any]) -> None:
        """Only unverified events may enter human verification. This
        protects the single-step decision workflow: a decided event is
        terminal and immutable (BR-V-01), so a second decision is a
        conflict carrying the first one, never an overwrite.
        """
        if status != UNVERIFIED:
            raise AlreadyDecidedError(existing_decision)

    @staticmethod
    def decided_status_for(decision: str) -> str:
        """The one legal target status per decision type — TRD 11.2.
        No 'auto_accepted', no 'escalated': their absence is the
        architecture, not an omission."""
        mapping = {"accept": "accepted", "reject": "rejected", "correct": "corrected"}
        return mapping[decision]
