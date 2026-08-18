"""RetentionGuard — BR-009: deletion enforced and recorded. [V1] stub.

MOD-11 (Retention Worker) is [V1] (TRD 4.1), and BACKEND_CODING_RULES 4
forbids implementing [V1] functionality in MVP. The guard object exists now
so the seven-guard surface of TRD 6.3 is complete and the [V1] work has a
named home; every method fails loudly rather than pretending retention is
enforced. The MVP gap is recorded honestly in DATABASE.md 9.5.
"""

from __future__ import annotations


class RetentionGuard:
    @staticmethod
    def ensure_deletion_recorded(*_args: object, **_kwargs: object) -> None:
        """[V1] — retention deletion must write an audit entry recording
        identifiers, status, period and count only (DATABASE.md 10.3)."""
        raise NotImplementedError(
            "RetentionGuard is [V1] — MOD-11 does not exist at MVP; "
            "see DATABASE.md 9.5 for the honestly-recorded gap"
        )

    @staticmethod
    def ensure_within_policy(*_args: object, **_kwargs: object) -> None:
        """[V1] — no read may serve data past its retention period."""
        raise NotImplementedError(
            "RetentionGuard is [V1] — MOD-11 does not exist at MVP"
        )
