"""EventRepository — events and event_corrections.

Two visibility rules are enforced at this level so no caller can bypass
them (TRD 6.4):

  * every scoped read filters on the caller's permitted site set — an
    authorisation bug in a controller cannot leak another site's events
    (TRD 12.3 enforcement point 2); and
  * every reporting read carries the RejectionExclusionGuard predicate —
    rejected, expired and unverified candidates cannot appear in any count
    (BR-R-01).

Pagination is cursor-based on (received_at, id). OFFSET is rejected in
review because the queue moves under the reader as decisions land — a
reviewer would see duplicates and skips (DATABASE.md 7.3).
"""

from __future__ import annotations

import base64
import binascii
from collections.abc import Iterable, Sequence
from datetime import datetime, timedelta
from typing import Any
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.orm import Session

from guardian_lens.core.errors import MalformedRequestError
from guardian_lens.guards.rejection_exclusion import RejectionExclusionGuard
from guardian_lens.repositories.tables import (
    cameras,
    detection_rules,
    event_corrections,
    events,
    users,
    model_versions,
    zones,
)

__all__ = ["EventRepository", "encode_cursor", "decode_cursor", "sessionize"]


def encode_cursor(received_at: datetime, event_id: UUID) -> str:
    raw = f"{received_at.isoformat()}|{event_id}"
    return base64.urlsafe_b64encode(raw.encode()).decode()


def decode_cursor(cursor: str) -> tuple[datetime, UUID]:
    try:
        raw = base64.urlsafe_b64decode(cursor.encode()).decode()
        ts, _, ident = raw.partition("|")
        return datetime.fromisoformat(ts), UUID(ident)
    except (ValueError, binascii.Error) as exc:
        raise MalformedRequestError("invalid cursor") from exc


def sessionize(rows: Sequence[sa.Row], gap_seconds: int) -> list[list[sa.Row]]:
    """Group rows into incidents: same rule, consecutive, gap ≤ window.

    Display-level only — every candidate in a group is still decided
    individually (BR-V-02 forbids bulk disposition; grouping collapses the
    QUEUE VIEW, never the decisions). Rows must arrive ordered by
    (rule_id, occurred_at). A row with no rule (an NVR event) never groups:
    "the same condition is continuing" is a claim only a rule can back.
    """
    gap = timedelta(seconds=gap_seconds)
    groups: list[list[sa.Row]] = []
    for row in rows:
        current = groups[-1] if groups else None
        if (
            current is not None
            and row.rule_id is not None
            and current[-1].rule_id == row.rule_id
            and row.occurred_at - current[-1].occurred_at <= gap
        ):
            current.append(row)
        else:
            groups.append([row])
    return groups


class EventRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    # -- ingest --------------------------------------------------------------

    def get_by_agent_event_id(self, event_id: UUID) -> sa.Row | None:
        """Dedup lookup on the agent-generated event_id (IF-C1)."""
        return self._session.execute(
            sa.select(events).where(events.c.event_id == event_id)
        ).one_or_none()

    def insert_candidate(self, values: dict[str, Any]) -> sa.Row:
        """Insert an unverified candidate; the caller owns the transaction.

        status is not a parameter: a candidate can only ever be born
        'unverified' (BR-004), which the column default provides.
        """
        return self._session.execute(
            sa.insert(events).values(**values).returning(events)
        ).one()

    # -- queue and detail ----------------------------------------------------

    def queue_page(
        self,
        *,
        site_ids: Iterable[UUID],
        status: str,
        limit: int,
        cursor: str | None = None,
        site_id: UUID | None = None,
        camera_id: UUID | None = None,
        zone_id: UUID | None = None,
        rule_id: UUID | None = None,
        occurred_from: datetime | None = None,
        occurred_to: datetime | None = None,
    ) -> tuple[Sequence[sa.Row], str | None, int]:
        """One page of the queue plus queue_depth, oldest first.

        ``site_ids`` is the caller's PERMITTED set from the token, applied
        unconditionally; ``site_id`` is an optional narrowing filter that
        can only shrink it, never widen it.
        """
        conditions = [
            events.c.site_id.in_(list(site_ids)),
            events.c.status == status,
        ]
        if site_id is not None:
            conditions.append(events.c.site_id == site_id)
        if camera_id is not None:
            conditions.append(events.c.camera_id == camera_id)
        if zone_id is not None:
            conditions.append(events.c.zone_id == zone_id)
        if rule_id is not None:
            conditions.append(events.c.rule_id == rule_id)
        if occurred_from is not None:
            conditions.append(events.c.occurred_at >= occurred_from)
        if occurred_to is not None:
            conditions.append(events.c.occurred_at <= occurred_to)

        query = (
            sa.select(
                events.c.id,
                events.c.event_id,
                events.c.camera_id,
                cameras.c.name.label("camera_name"),
                events.c.zone_id,
                zones.c.name.label("zone_name"),
                detection_rules.c.human_readable.label("rule_human_readable"),
                events.c.rule_snapshot,
                events.c.source,
                events.c.confidence,
                events.c.occurred_at,
                events.c.received_at,
                events.c.status,
                events.c.evidence_state,
                events.c.version,
                # FR-013 — the analysing model, named on every capture.
                model_versions.c.version.label("model_version"),
            )
            .select_from(
                events.join(cameras, events.c.camera_id == cameras.c.id)
                .outerjoin(zones, events.c.zone_id == zones.c.id)
                .outerjoin(
                    detection_rules, events.c.rule_id == detection_rules.c.id
                )
                .outerjoin(
                    model_versions,
                    events.c.model_version_id == model_versions.c.id,
                )
            )
            .where(*conditions)
            .order_by(events.c.received_at.asc(), events.c.id.asc())
            .limit(limit + 1)  # one extra row decides has-more
        )
        if cursor is not None:
            after_ts, after_id = decode_cursor(cursor)
            query = query.where(
                sa.tuple_(events.c.received_at, events.c.id)
                > sa.tuple_(
                    sa.literal(after_ts, _ts_type), sa.literal(after_id, _id_type)
                )
            )

        rows = self._session.execute(query).all()
        next_cursor = None
        if len(rows) > limit:
            rows = rows[:limit]
            last = rows[-1]
            next_cursor = encode_cursor(last.received_at, last.id)

        # queue_depth on every queue response — DP-4 without a second
        # request (TRD 10.4). Depth of the whole filtered set, not the page.
        depth = self._session.execute(
            sa.select(sa.func.count()).select_from(events).where(*conditions)
        ).scalar_one()
        return rows, next_cursor, int(depth)

    def incident_rows(
        self,
        *,
        site_ids: Iterable[UUID],
        status: str,
        max_rows: int,
        site_id: UUID | None = None,
    ) -> tuple[Sequence[sa.Row], int, bool]:
        """Every queue row for sessionization, ordered (rule_id, occurred_at).

        Returns (rows, queue_depth, capped). ``capped`` is True when the
        scan stopped at ``max_rows`` — the caller must surface it, never
        present a truncated grouping as complete (no silent caps).
        """
        conditions = [
            events.c.site_id.in_(list(site_ids)),
            events.c.status == status,
        ]
        if site_id is not None:
            conditions.append(events.c.site_id == site_id)

        rows = self._session.execute(
            sa.select(
                events.c.id,
                events.c.rule_id,
                events.c.camera_id,
                cameras.c.name.label("camera_name"),
                events.c.zone_id,
                zones.c.name.label("zone_name"),
                detection_rules.c.human_readable.label("rule_human_readable"),
                events.c.rule_snapshot,
                events.c.confidence,
                events.c.occurred_at,
                events.c.received_at,
                events.c.status,
                events.c.evidence_state,
                events.c.version,
            )
            .select_from(
                events.join(cameras, events.c.camera_id == cameras.c.id)
                .outerjoin(zones, events.c.zone_id == zones.c.id)
                .outerjoin(
                    detection_rules, events.c.rule_id == detection_rules.c.id
                )
            )
            .where(*conditions)
            # NULL rules last so ungroupable rows cannot split a session.
            .order_by(
                events.c.rule_id.asc().nulls_last(),
                events.c.occurred_at.asc(),
                events.c.id.asc(),
            )
            .limit(max_rows + 1)
        ).all()

        capped = len(rows) > max_rows
        if capped:
            rows = rows[:max_rows]
        depth = self._session.execute(
            sa.select(sa.func.count()).select_from(events).where(*conditions)
        ).scalar_one()
        return rows, int(depth), capped

    def get_scoped(self, event_pk: UUID, site_ids: Iterable[UUID]) -> sa.Row | None:
        """One event, only if it lies inside the caller's site scope.
        Out-of-scope and non-existent are indistinguishable to the caller.

        Joined the same way as queue_page — the detail view is a superset
        of a queue row (every events.* column, plus the display names the
        review UI needs), never a disjoint shape."""
        return self._session.execute(
            sa.select(
                events,
                cameras.c.name.label("camera_name"),
                zones.c.name.label("zone_name"),
                detection_rules.c.human_readable.label("rule_human_readable"),
                # BR-005 made visible: the reviewer NAME travels with the
                # decided event, not just the id.
                users.c.full_name.label("reviewer_full_name"),
            )
            .select_from(
                events.join(cameras, events.c.camera_id == cameras.c.id)
                .outerjoin(zones, events.c.zone_id == zones.c.id)
                .outerjoin(
                    detection_rules, events.c.rule_id == detection_rules.c.id
                )
                .outerjoin(users, events.c.reviewer_id == users.c.id)
            )
            .where(
                events.c.id == event_pk,
                events.c.site_id.in_(list(site_ids)),
            )
        ).one_or_none()

    def get(self, event_pk: UUID) -> sa.Row | None:
        """Unscoped fetch for the decision path, which distinguishes 404
        (absent) from 403 (present, out of scope) per the D2 ladder."""
        return self._session.execute(
            sa.select(events).where(events.c.id == event_pk)
        ).one_or_none()

    # -- decision ------------------------------------------------------------

    def apply_decision(
        self,
        event_pk: UUID,
        expected_version: int,
        values: dict[str, Any],
    ) -> sa.Row | None:
        """Conditional update: succeeds only against the expected version of
        a still-unverified row. Returns the updated row or None — the
        optimistic-lock and concurrent-decision handling the TRD requires
        (BACKEND_CODING_RULES 26). Runs inside the caller's transaction."""
        return self._session.execute(
            sa.update(events)
            .where(
                events.c.id == event_pk,
                events.c.version == expected_version,
                events.c.status == "unverified",
            )
            .values(version=events.c.version + 1, **values)
            .returning(events)
        ).one_or_none()

    def insert_correction(
        self,
        event_pk: UUID,
        field_name: str,
        original_value: str,
        corrected_value: str,
        corrected_by: UUID,
    ) -> None:
        """Insert-only: the model's original value is retained as the only
        ground truth the product ever collects (DATABASE.md 5.6)."""
        self._session.execute(
            sa.insert(event_corrections).values(
                event_id=event_pk,
                field_name=field_name,
                original_value=original_value,
                corrected_value=corrected_value,
                corrected_by=corrected_by,
            )
        )

    # -- reporting (verified only — BR-R-01) ---------------------------------

    def verified_counts(
        self,
        *,
        site_id: UUID,
        occurred_from: datetime,
        occurred_to: datetime,
        group_by: str,
        site_timezone: str,
    ) -> Sequence[sa.Row]:
        """Counts grouped by zone, rule or day. The verified-only predicate
        comes from the guard and is not a parameter — no caller can omit it."""
        if group_by == "zone":
            label = sa.func.coalesce(zones.c.name, sa.literal("(zone removed)"))
            source = events.outerjoin(zones, events.c.zone_id == zones.c.id)
        elif group_by == "rule":
            # rule_snapshot, not the live rule row: the snapshot is what
            # actually fired, and it survives rule deletion (DATABASE.md 5.5).
            label = events.c.rule_snapshot["rule_type"].astext
            source = events
        elif group_by == "day":
            # Days are the SITE's days: a reporting period is a shift
            # boundary and a shift belongs to the site, not to whoever opens
            # the report (NFR-L-02, sites.timezone).
            label = sa.cast(
                sa.func.timezone(site_timezone, events.c.occurred_at), sa.Date
            )
            source = events
        else:
            raise ValueError(f"unsupported group_by {group_by!r}")

        return self._session.execute(
            sa.select(label.label("group_label"), sa.func.count().label("verified_count"))
            .select_from(source)
            .where(
                RejectionExclusionGuard.verified_only(events.c.status),
                events.c.site_id == site_id,
                events.c.occurred_at >= occurred_from,
                events.c.occurred_at <= occurred_to,
            )
            .group_by(label)
            .order_by(label)
        ).all()

    def decision_counts(
        self, *, site_id: UUID, occurred_from: datetime, occurred_to: datetime
    ) -> dict[str, int]:
        """Accepted/corrected/rejected counts — BR-R-03 makes the system's
        own error rate visible, never hidden. Counts only; the rejected
        events themselves stay out of every report body (BR-R-01)."""
        rows = self._session.execute(
            sa.select(events.c.status, sa.func.count())
            .where(
                events.c.site_id == site_id,
                events.c.occurred_at >= occurred_from,
                events.c.occurred_at <= occurred_to,
                events.c.status.in_(["accepted", "corrected", "rejected"]),
            )
            .group_by(events.c.status)
        ).all()
        counts = {"accepted": 0, "corrected": 0, "rejected": 0}
        for status, count in rows:
            counts[status] = int(count)
        return counts


_ts_type = events.c.received_at.type
_id_type = events.c.id.type
