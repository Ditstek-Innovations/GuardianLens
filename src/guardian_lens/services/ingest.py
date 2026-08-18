"""EventIngestService — MOD-6: validate, deduplicate, persist, store frame.

Agent principals only; the route enforces that before this service runs.
One transaction per event (TRD 6.2). Idempotent on the agent-generated
event_id: a duplicate returns the existing record and creates nothing
(IF-C1), because the edge publisher delivers at-least-once and dedup
belongs at the receiver (IF-E5).

The forbidden-field rule (status/reviewer_id/decided_at → 400, BR-004) is
checked by the controller against the RAW body before Pydantic runs, so a
rule violation is never mistaken for a validation slip.
"""

from __future__ import annotations

import base64
import binascii
import logging
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from sqlalchemy.exc import IntegrityError

from guardian_lens.core.errors import (
    PayloadTooLargeError,
    ValidationFailureError,
)
from guardian_lens.core.logging import get_logger, log_event
from guardian_lens.core.principal import AgentPrincipal
from guardian_lens.repositories.config import ConfigRepository
from guardian_lens.repositories.events import EventRepository
from guardian_lens.repositories.evidence import EvidenceStore, make_evidence_key
from guardian_lens.repositories.identity import IdentityRepository
from guardian_lens.schemas.events import EventIngestRequest
from guardian_lens.tenancy.context import TenantContext

__all__ = ["EventIngestService", "IngestOutcome"]

_log = get_logger("guardian_lens.ingest")


class IngestOutcome:
    """The persisted row plus whether this call created it — the controller
    maps created=False to 200 instead of 201 (TRD 10.3)."""

    __slots__ = ("row", "created")

    def __init__(self, row: Any, created: bool) -> None:
        self.row = row
        self.created = created


class EventIngestService:
    def __init__(
        self,
        context: TenantContext,
        evidence_store: EvidenceStore,
        *,
        evidence_max_bytes: int,
        clock_skew_tolerance_seconds: int,
    ) -> None:
        self._context = context
        self._session = context.session
        self._events = EventRepository(context.session)
        self._config = ConfigRepository(context.session)
        self._evidence_store = evidence_store
        self._evidence_max_bytes = evidence_max_bytes
        self._skew_tolerance = timedelta(seconds=clock_skew_tolerance_seconds)

    def ingest(
        self, request: EventIngestRequest, agent: AgentPrincipal
    ) -> IngestOutcome:
        existing = self._events.get_by_agent_event_id(request.event_id)
        if existing is not None:
            return IngestOutcome(existing, created=False)

        self._validate_references(request, agent)
        frame = self._decode_evidence(request)

        received_at = datetime.now(timezone.utc)
        values: dict[str, Any] = {
            "event_id": request.event_id,
            "camera_id": request.camera_id,
            "zone_id": request.zone_id,
            "rule_id": request.rule_id,
            "rule_snapshot": request.rule_snapshot,
            "source": request.source,
            "agent_id": agent.agent_id,
            "confidence": request.confidence,
            "occurred_at": request.occurred_at,
            "received_at": received_at,
        }
        # site_id is derived by the site-consistency trigger from the
        # camera; supplying it from here would only duplicate that logic.

        if request.source == "guardian_lens":
            model_id = self._config.model_version_id(request.model_version or "")
            if model_id is None:
                raise ValidationFailureError(
                    "model_version is not a registered model version",
                    field="model_version",
                )
            values["model_version_id"] = model_id

        if frame is not None:
            key = make_evidence_key(
                self._context.tenant_slug,
                agent.site_id,
                request.event_id,
                received_at,
            )
            # Store the frame before the row: an evidence_ref pointing at
            # nothing is a reconciliation defect (DATABASE.md 12.3), while
            # an orphan object on a failed insert is swept later.
            self._evidence_store.put(key, frame)
            values["evidence_ref"] = key
            values["evidence_state"] = "present"
            values["evidence_blurred"] = request.evidence.blurred  # type: ignore[union-attr]
        else:
            values["evidence_state"] = "none"

        try:
            row = self._events.insert_candidate(values)
            self._session.commit()
        except IntegrityError:
            # Two deliveries raced past the dedup read. The unique
            # constraint on event_id is the authority; return the winner.
            self._session.rollback()
            existing = self._events.get_by_agent_event_id(request.event_id)
            if existing is None:  # pragma: no cover — some other violation
                raise
            return IngestOutcome(existing, created=False)

        log_event(
            _log,
            "event.ingested",
            channel="application",
            event_ref=str(row.id),
            source=request.source,
        )
        return IngestOutcome(row, created=True)

    # -- agent telemetry (TRD 10.3: health beat, gap reporting) --------------

    def record_health(
        self,
        agent: AgentPrincipal,
        *,
        sent_at: datetime,
        applied_config_version: int | None,
        agent_version: str | None,
    ) -> int:
        """Apply a health beat; returns the measured clock skew.

        clock_skew_ms = received - sent (ADR-007): the skew is recorded,
        never used to correct timestamps — a corrected timestamp is a
        fabricated observation.
        """
        received = datetime.now(timezone.utc)
        skew_ms = int((received - sent_at).total_seconds() * 1000)
        IdentityRepository(self._session).record_agent_health(
            agent.agent_id,
            clock_skew_ms=skew_ms,
            applied_config_version=applied_config_version,
            agent_version=agent_version,
        )
        self._session.commit()
        return skew_ms

    def record_coverage_gap(
        self,
        agent: AgentPrincipal,
        *,
        gap_id: UUID,
        camera_id: UUID | None,
        started_at: datetime,
        ended_at: datetime | None,
        reason: str,
        detail: str | None,
    ) -> None:
        """Idempotent upsert keyed on the edge-generated gap id. The site
        and agent attribution come from the token, never the body."""
        if camera_id is not None:
            camera_site = self._config.camera_site(camera_id)
            if camera_site is None or camera_site != agent.site_id:
                raise ValidationFailureError(
                    "camera_id does not exist at this agent's site",
                    field="camera_id",
                )
        self._config.upsert_coverage_gap(
            {
                "id": gap_id,
                "site_id": agent.site_id,
                "camera_id": camera_id,
                "agent_id": agent.agent_id,
                "started_at": started_at,
                "ended_at": ended_at,
                "reason": reason,
                "detail": detail,
                "recorded_by": "agent",
            }
        )
        self._session.commit()
        log_event(
            _log,
            "coverage_gap.recorded",
            level=logging.INFO,
            channel="application",
            gap_reason=reason,
        )

    # -- internal ------------------------------------------------------------

    def _validate_references(
        self, request: EventIngestRequest, agent: AgentPrincipal
    ) -> None:
        camera_site = self._config.camera_site(request.camera_id)
        if camera_site is None or camera_site != agent.site_id:
            # A camera outside the agent's own site is indistinguishable
            # from a nonexistent one: agents are site-bound at registration.
            raise ValidationFailureError(
                "camera_id does not exist at this agent's site",
                field="camera_id",
            )
        if request.zone_id is not None and not self._config.zone_exists(
            request.zone_id
        ):
            raise ValidationFailureError("zone_id does not exist", field="zone_id")
        if request.rule_id is not None and not self._config.rule_exists(
            request.rule_id
        ):
            raise ValidationFailureError("rule_id does not exist", field="rule_id")

        now = datetime.now(timezone.utc)
        if request.occurred_at > now + self._skew_tolerance:
            raise ValidationFailureError(
                "occurred_at is in the future beyond clock-skew tolerance",
                field="occurred_at",
            )

    def _decode_evidence(self, request: EventIngestRequest) -> bytes | None:
        if request.evidence is None:
            return None
        encoded = request.evidence.data_b64
        # Size gate on the encoded form first, so a hostile payload cannot
        # force a huge decode before being rejected.
        if len(encoded) > self._evidence_max_bytes * 4 // 3 + 4:
            raise PayloadTooLargeError("evidence exceeds the size limit")
        try:
            frame = base64.b64decode(encoded, validate=True)
        except (ValueError, binascii.Error) as exc:
            raise ValidationFailureError(
                "evidence.data_b64 is not valid base64", field="evidence.data_b64"
            ) from exc
        if len(frame) > self._evidence_max_bytes:
            raise PayloadTooLargeError("evidence exceeds the size limit")
        return frame
