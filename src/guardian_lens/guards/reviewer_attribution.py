"""ReviewerAttributionGuard — BR-005, BR-S-01: reviewer from session only.

Two directions, both enforced:

  * a client may never SUPPLY attribution — reviewer_id, status or
    decided_at arriving in any request body is a 400, not a 422, because
    it is an attempted rule violation rather than a validation slip; and
  * the server may never OMIT attribution — a decision without an
    authenticated reviewer identity must not proceed.
"""

from __future__ import annotations

from collections.abc import Iterable
from uuid import UUID

from guardian_lens.core.errors import ForbiddenFieldError

#: Server-owned fields that no client — agent or human — may ever submit.
#: TRD 10.3 names status/reviewer_id/decided_at on ingest (BR-004);
#: TRD 10.4 names reviewer_id on decision (BR-S-01). decision_type is the
#: same class of field by construction.
SERVER_OWNED_FIELDS = frozenset(
    {"status", "reviewer_id", "decided_at", "decision_type"}
)


class ReviewerAttributionGuard:
    @staticmethod
    def ensure_no_client_attribution(body_keys: Iterable[str]) -> None:
        """Reject any body carrying a server-owned field. Checked against
        the RAW body keys, before schema validation, so the response is the
        rule's 400 and never a generic 422."""
        offending = SERVER_OWNED_FIELDS.intersection(body_keys)
        if offending:
            field = sorted(offending)[0]
            raise ForbiddenFieldError(
                f"'{field}' is never accepted from a client; reviewer "
                f"identity and event status are server-owned (BR-004, BR-S-01)",
                field=field,
            )

    @staticmethod
    def ensure_attributed(reviewer_id: UUID | None) -> None:
        """A decision must carry the authenticated reviewer. This cannot
        fire on any current path — identity comes from a verified token —
        but the guard states the invariant so a future path cannot drop it
        silently."""
        if reviewer_id is None:
            raise ValueError(
                "decision without an authenticated reviewer (BR-005); "
                "this is a programming error, not a client error"
            )
