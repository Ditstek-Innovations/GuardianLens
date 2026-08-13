"""RejectionExclusionGuard — BR-R-01: reports draw from verified records only.

The filter lives here, in ONE place, and the reporting repository applies
it to every verified-read statement — so no caller can construct a report
query that includes rejected, expired or unverified candidates
(TRD 6.4: enforced at the repository level, not per caller).
"""

from __future__ import annotations

from sqlalchemy import Column
from sqlalchemy.sql.elements import ColumnElement

#: The two — and only two — statuses that appear in reports (TRD 11.2).
VERIFIED_STATUSES: tuple[str, str] = ("accepted", "corrected")


class RejectionExclusionGuard:
    @staticmethod
    def verified_only(status_column: Column) -> ColumnElement[bool]:
        """The mandatory predicate for every reporting read. Composing a
        report query without this call is unrepresentable through the
        repository interface — the query builder inspection test asserts
        the emitted SQL carries it (TRD 6.3)."""
        return status_column.in_(VERIFIED_STATUSES)
