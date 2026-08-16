"""AuditWriteGuard — BR-010, BR-AU-01: every mutation audited, allowlisted.

Two responsibilities:

  * FIELD ALLOWLIST per entity type (DATABASE.md 10.3) — before/after
    states are filtered to the named fields, never "the whole row". A naive
    whole-row copy would put cameras.stream_url_encrypted into a JSONB
    column with none of that column's protections, turning the audit log
    into the credential store's weakest replica (DATABASE.md 8.3).
  * FORBIDDEN fields (DATABASE.md 10.4) raise loudly rather than being
    dropped: offering credential material for audit is a programming error
    that must fail the transaction, not a value to be quietly discarded.

Append-only is enforced twice elsewhere: AuditRepository exposes no update
or delete method at all, and the database triggers reject the operations
regardless of caller. Only the second survives a direct connection.
"""

from __future__ import annotations

from typing import Any

from guardian_lens.core.errors import AuditFieldError

#: DATABASE.md 10.4 — must never enter the audit log, under any entity type.
FORBIDDEN_AUDIT_FIELDS = frozenset(
    {
        "stream_url",
        "stream_url_encrypted",
        "password",
        "password_hash",
        "credential_hash",
        "access_token",
        "refresh_token",
        "token_hash",
        "data_b64",
    }
)

#: DATABASE.md 10.3 — the allowlist, per entity type. Fields not listed are
#: rejected, not silently kept: fail closed.
AUDIT_FIELD_ALLOWLIST: dict[str, frozenset[str]] = {
    "event": frozenset(
        {
            "status", "version", "reviewer_id", "decision_type", "decided_at",
            "rejection_reason", "zone_id", "rule_id",
        }
    ),
    "rule": frozenset(
        {
            "zone_id", "rule_type", "is_active", "confidence_threshold",
            "debounce_seconds", "dwell_seconds", "human_readable",
            "written_rule_reference", "detection_class",
            "must_be_carried", "activated_by",
            "activated_at", "deactivated_at",
        }
    ),
    "camera": frozenset(
        {
            "site_id", "name", "location_description", "stream_profile",
            "sample_rate_fps", "status", "stream_url_key_id",
        }
    ),
    "zone": frozenset({"camera_id", "name", "polygon"}),
    "site": frozenset({"name", "timezone"}),
    "user": frozenset({"email", "full_name", "is_active"}),
    "user_role": frozenset({"role", "site_id"}),
    "agent": frozenset({"site_id", "name", "status"}),
    # Gate G1 evidence trail — DATABASE.md 10.3 `model.registered` row
    # ("Version, hashes, approver"), realised by migration 0004.
    "model_version": frozenset(
        {
            "version", "artefact_hash", "training_data_hash", "classes",
            "model_card_ref", "datasheet_ref", "approved_by", "approved_at",
            "notes",
        }
    ),
    "auth": frozenset({"attempts", "window_seconds"}),
}


class AuditWriteGuard:
    @staticmethod
    def filter_state(
        entity_type: str, state: dict[str, Any] | None
    ) -> dict[str, Any] | None:
        """Validate a before/after state against the allowlist.

        Raises AuditFieldError — failing the surrounding transaction — on a
        forbidden field, an unlisted field, or an unknown entity type.
        """
        if state is None:
            return None
        allowed = AUDIT_FIELD_ALLOWLIST.get(entity_type)
        if allowed is None:
            raise AuditFieldError(
                f"no audit allowlist exists for entity type '{entity_type}'"
            )
        for key in state:
            if key in FORBIDDEN_AUDIT_FIELDS:
                raise AuditFieldError(
                    f"'{key}' must never enter the audit log (DATABASE.md 10.4)"
                )
            if key not in allowed:
                raise AuditFieldError(
                    f"'{key}' is not in the audit allowlist for '{entity_type}'"
                )
        # Values pass through unchanged; only keys are policed. JSON
        # serialisability is the repository's concern.
        return dict(state)
