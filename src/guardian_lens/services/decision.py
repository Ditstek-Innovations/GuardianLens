"""DecisionService — MOD-7: apply one reviewer decision to one event.

This is ARCHITECTURE.md 5.5's D2 ladder as code, in the ladder's order.
Every 4xx branch is a rule, not an error case:

    agent principal        → 403  (BR-S-02, enforced at the route)
    role does not decide   → 403  (enforced at the route)
    out of site scope      → 403
    reviewer_id in body    → 400  (BR-S-01)
    status not unverified  → 409 + existing decision (BR-V-01)
    stale version          → 409

The decision update and its audit entry share ONE transaction (BR-AU-03):
if the audit write fails, the decision rolls back, because a decision that
cannot be audited must not exist (TRD 11.3). There is deliberately no bulk
variant of this operation anywhere (TRD 10.9).
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

import sqlalchemy as sa

from guardian_lens.schemas.validation import validate_model
from guardian_lens.core.errors import (
    AlreadyDecidedError,
    NotFoundError,
    ScopeError,
    ValidationFailureError,
    VersionConflictError,
)
from guardian_lens.core.principal import DECIDE_ROLES, HumanPrincipal
from guardian_lens.guards.reviewer_attribution import ReviewerAttributionGuard
from guardian_lens.guards.verification import VerificationGuard
from guardian_lens.repositories.config import ConfigRepository
from guardian_lens.repositories.events import EventRepository
from guardian_lens.repositories.identity import IdentityRepository
from guardian_lens.schemas.events import DecisionRequest
from guardian_lens.services.audit import AuditService
from guardian_lens.tenancy.context import TenantContext

__all__ = ["DecisionService", "CORRECTABLE_FIELDS"]

#: The event fields a 'correct' decision may amend. The model's zone or
#: rule attribution can be wrong; its existence, timing and evidence are
#: observations and are not correctable.
CORRECTABLE_FIELDS = frozenset({"zone_id", "rule_id"})


class DecisionService:
    def __init__(self, context: TenantContext, audit: AuditService) -> None:
        self._context = context
        self._session = context.session
        self._events = EventRepository(context.session)
        self._config = ConfigRepository(context.session)
        self._audit = audit

    def apply_decision(
        self,
        *,
        event_pk: UUID,
        principal: HumanPrincipal,
        body: dict[str, Any],
        ip_address: str | None,
    ) -> dict[str, Any]:
        # The body arrives RAW, not model-validated: the ladder places the
        # scope 403 before the forbidden-field 400 and both before any
        # generic 422, so validation must happen inside the ladder, not in
        # front of it.

        # Ladder steps 1–2 (principal type, role) are route dependencies;
        # from here the caller is a human holding a deciding role.

        event = self._events.get(event_pk)
        if event is None:
            raise NotFoundError("event not found")

        # Step 3 — site + zone scope. Zone scoping is site-wide at MVP
        # (user_zone_scopes is [V1]); the site check is the enforced scope.
        if not principal.holds_at_site(DECIDE_ROLES, event.site_id):
            raise ScopeError("event is outside your site scope")

        # Step 4 — server-owned fields in the body → 400, never 422.
        ReviewerAttributionGuard.ensure_no_client_attribution(body.keys())
        ReviewerAttributionGuard.ensure_attributed(principal.user_id)

        request = validate_model(DecisionRequest, body)
        decision = request.decision
        rejection_reason = request.rejection_reason
        training_feedback = request.training_feedback
        corrections = (
            [item.model_dump() for item in request.corrections]
            if request.corrections is not None
            else None
        )

        # Step 5 — only unverified events may enter verification.
        VerificationGuard.ensure_undecided(
            event.status, self._existing_decision(event)
        )

        # Step 6 is the conditional UPDATE below: checking the version here
        # and updating later would leave a race window; the WHERE clause is
        # the check.

        if decision == "reject" and not (rejection_reason or "").strip():
            raise ValidationFailureError(
                "rejection_reason is required when decision is reject",
                field="rejection_reason",
            )
        if decision != "reject" and training_feedback is not None:
            raise ValidationFailureError(
                "training_feedback is only valid when decision is reject",
                field="training_feedback",
            )

        values: dict[str, Any] = {
            "status": VerificationGuard.decided_status_for(decision),
            "reviewer_id": principal.user_id,
            "decided_at": sa.func.now(),
            "decision_type": decision,
            "rejection_reason": (
                rejection_reason if decision == "reject" else None
            ),
        }
        correction_pairs = self._validate_corrections(decision, corrections, event)
        for field_name, corrected_value in correction_pairs:
            values[field_name] = corrected_value

        updated = self._events.apply_decision(event_pk, request.version, values)
        if updated is None:
            # The row moved under us: either another decision landed
            # (status left 'unverified') or the caller's version is stale.
            current = self._events.get(event_pk)
            if current is not None and current.status != "unverified":
                raise AlreadyDecidedError(self._existing_decision(current))
            raise VersionConflictError("version does not match current event")

        for field_name, corrected_value in correction_pairs:
            self._events.insert_correction(
                event_pk,
                field_name,
                str(getattr(event, field_name)),
                str(corrected_value),
                principal.user_id,
            )

        training_class = event.predicted_class
        corrected_rule = next(
            (
                value
                for field_name, value in correction_pairs
                if field_name == "rule_id"
            ),
            None,
        )
        if corrected_rule is not None:
            training_class = self._config.rule_detection_class(corrected_rule)
        has_training_annotation = (
            event.evidence_ref is not None
            and training_class is not None
            and event.predicted_bbox is not None
        )
        self._events.insert_training_sample(
            event_id=event_pk,
            site_id=event.site_id,
            decision_type=decision,
            class_name=training_class,
            bbox_norm=(
                list(event.predicted_bbox)
                if event.predicted_bbox is not None
                else None
            ),
            eligible=(
                (
                    decision in {"accept", "correct"}
                    or (decision == "reject" and training_feedback == "false_positive")
                )
                and has_training_annotation
            ),
            reviewed_by=principal.user_id,
        )

        # Same transaction as the update above — BR-AU-03. If this raises,
        # the surrounding rollback discards the decision entirely.
        self._audit.write(
            action="event.decided",
            entity_type="event",
            actor_user_id=principal.user_id,
            entity_id=event_pk,
            before_state={"status": event.status, "version": event.version},
            after_state={
                "status": updated.status,
                "version": updated.version,
                "reviewer_id": str(principal.user_id),
                "decision_type": decision,
                "decided_at": updated.decided_at.isoformat(),
            },
            ip_address=ip_address,
        )
        if correction_pairs:
            self._audit.write(
                action="event.corrected",
                entity_type="event",
                actor_user_id=principal.user_id,
                entity_id=event_pk,
                before_state={
                    f: str(getattr(event, f)) for f, _ in correction_pairs
                },
                after_state={f: str(v) for f, v in correction_pairs},
                ip_address=ip_address,
            )

        self._session.commit()

        reviewer = IdentityRepository(self._session).user_by_id(principal.user_id)
        return {
            "id": updated.id,
            "status": updated.status,
            "reviewer": {
                "id": principal.user_id,
                "full_name": reviewer.full_name if reviewer else "",
            },
            "decided_at": updated.decided_at,
            "decision_type": updated.decision_type,
            "version": updated.version,
        }

    # -- internal ------------------------------------------------------------

    def _validate_corrections(
        self,
        decision: str,
        corrections: list[dict[str, str]] | None,
        event: sa.Row,
    ) -> list[tuple[str, UUID]]:
        if decision != "correct":
            if corrections:
                raise ValidationFailureError(
                    "corrections are only valid when decision is correct",
                    field="corrections",
                )
            return []
        if not corrections:
            raise ValidationFailureError(
                "at least one correction is required when decision is correct",
                field="corrections",
            )
        pairs: list[tuple[str, UUID]] = []
        for item in corrections:
            field_name = item.get("field", "")
            if field_name not in CORRECTABLE_FIELDS:
                raise ValidationFailureError(
                    f"field '{field_name}' is not correctable",
                    field="corrections",
                )
            try:
                value = UUID(item.get("value", ""))
            except ValueError:
                raise ValidationFailureError(
                    f"corrected value for '{field_name}' must be a UUID",
                    field="corrections",
                ) from None
            exists = (
                self._config.zone_exists(value)
                if field_name == "zone_id"
                else self._config.rule_exists(value)
            )
            if not exists:
                raise ValidationFailureError(
                    f"corrected {field_name} does not exist",
                    field="corrections",
                )
            pairs.append((field_name, value))
        return pairs

    @staticmethod
    def _existing_decision(event: sa.Row) -> dict[str, Any]:
        """The existing decision, for the 409 body (TRD 10.4)."""
        return {
            "id": str(event.id),
            "status": event.status,
            "decision_type": event.decision_type,
            "reviewer_id": str(event.reviewer_id) if event.reviewer_id else None,
            "decided_at": (
                event.decided_at.isoformat() if event.decided_at else None
            ),
            "version": event.version,
        }
