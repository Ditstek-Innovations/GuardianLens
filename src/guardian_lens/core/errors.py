"""Domain and application errors, mapped to the TRD 10.8 envelope.

Every error the API can return shares one shape:

    { "error": { "code": "GL-4221", "message": "...",
                 "field": "...", "trace_id": "uuid" } }

Expected business conditions are explicit exception types, never generic
exceptions (BACKEND_CODING_RULES 16). Each carries its HTTP status and a
``GL-`` code from the TRD 10.8 range table, so the controller layer only
translates — it never decides.

The 409 "already decided" case additionally carries the existing decision:
TRD 10.4 requires the conflict response to return it, and the envelope has
no field for it, so it travels as an additive ``existing_decision`` key
inside ``error``. The four specified keys are always present.
"""

from __future__ import annotations

from typing import Any

__all__ = [
    "GuardianError",
    "MalformedRequestError",
    "ForbiddenFieldError",
    "InvalidResetTokenError",
    "AuthenticationError",
    "InvalidCredentialsError",
    "AuthorizationError",
    "PrincipalTypeError",
    "ScopeError",
    "TenantNotActiveError",
    "NotFoundError",
    "AlreadyDecidedError",
    "VersionConflictError",
    "PayloadTooLargeError",
    "ValidationFailureError",
    "RateLimitedError",
    "TenantBindingError",
    "AuditFieldError",
    "DependencyUnavailableError",
]


class GuardianError(Exception):
    """Base for every expected error. Subclasses fix status and code."""

    http_status: int = 500
    code: str = "GL-5000"

    def __init__(
        self,
        message: str,
        *,
        field: str | None = None,
        extra: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.field = field
        # Additive envelope keys (e.g. existing_decision on a 409).
        self.extra = extra or {}


class MalformedRequestError(GuardianError):
    """The body is not parseable JSON at all — GL-400x."""

    http_status = 400
    code = "GL-4001"


class ForbiddenFieldError(GuardianError):
    """A server-owned field arrived from a client — 400, never 422.

    This is a rule violation, not a validation slip: status/reviewer_id/
    decided_at from an agent is an attempt at BR-004, reviewer_id in a
    decision body is an attempt at BR-S-01. The distinct status code keeps
    the two failure classes separable in monitoring.
    """

    http_status = 400
    code = "GL-4002"


class InvalidResetTokenError(GuardianError):
    """Generic on purpose: identical for unknown address, wrong user,
    expired, spent and forged tokens, so the reset route cannot be used to
    probe which of them it was (CS-AU-17)."""

    http_status = 400
    code = "GL-4003"

    def __init__(self) -> None:
        super().__init__("The reset link is invalid or has expired.")


class AuthenticationError(GuardianError):
    http_status = 401
    code = "GL-4010"


class InvalidCredentialsError(GuardianError):
    """Generic on purpose: identical for unknown address and wrong password,
    so the login route cannot be used to enumerate users (DATABASE.md 1.5)."""

    http_status = 401
    code = "GL-4011"

    def __init__(self) -> None:
        super().__init__("invalid credentials")


class AuthorizationError(GuardianError):
    http_status = 403
    code = "GL-4030"


class PrincipalTypeError(GuardianError):
    """Wrong kind of principal: agent on a human route or the reverse."""

    http_status = 403
    code = "GL-4031"


class ScopeError(GuardianError):
    """Authenticated, role held, but the target is outside site/zone scope."""

    http_status = 403
    code = "GL-4032"


class TenantNotActiveError(GuardianError):
    """The tenant exists but must not be served (suspended/drifted/...).

    Fail closed: a tenant the router cannot positively confirm as active is
    refused, never served from a fallback (BACKEND_CODING_RULES 6.5).
    """

    http_status = 403
    code = "GL-4033"


class NotFoundError(GuardianError):
    """Absent — or present but outside the caller's scope. Reads return the
    same 404 for both so existence does not leak across scope boundaries."""

    http_status = 404
    code = "GL-4040"


class AlreadyDecidedError(GuardianError):
    """The event is terminal. Carries the existing decision (TRD 10.4)."""

    http_status = 409
    code = "GL-4090"

    def __init__(self, existing_decision: dict[str, Any]) -> None:
        super().__init__(
            "event is already decided (BR-V-01)",
            extra={"existing_decision": existing_decision},
        )


class VersionConflictError(GuardianError):
    """Optimistic-lock failure: the event changed under the caller."""

    http_status = 409
    code = "GL-4091"


class DuplicateResourceError(GuardianError):
    """A uniquely-identified resource already exists (or is already in the
    requested state) — GL-409x conflict range, TRD 10.8."""

    http_status = 409
    code = "GL-4092"


class PayloadTooLargeError(GuardianError):
    http_status = 413
    code = "GL-4130"


class ValidationFailureError(GuardianError):
    http_status = 422
    code = "GL-4220"


class RateLimitedError(GuardianError):
    http_status = 429
    code = "GL-4290"


class TenantBindingError(GuardianError):
    """tenant_identity did not match the bound tenant.

    A mis-routed connection is a P1 incident, never a retry
    (ARCHITECTURE.md 8.9.1). The pool is quarantined before this is raised;
    the client sees a generic 500 with no detail.
    """

    http_status = 500
    code = "GL-5001"


class AuditFieldError(GuardianError):
    """A state field outside the audit allowlist was offered for audit.

    A programming error, deliberately loud: silently dropping the field
    would let a future caller believe something was audited that was not,
    and silently keeping it is how stream_url_encrypted ends up in
    audit_log (DATABASE.md 10.4)."""

    http_status = 500
    code = "GL-5002"


class DependencyUnavailableError(GuardianError):
    http_status = 503
    code = "GL-5030"


def envelope(
    code: str,
    message: str,
    trace_id: str,
    field: str | None = None,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build the TRD 10.8 envelope. The only place its shape is written."""
    error: dict[str, Any] = {
        "code": code,
        "message": message,
        "field": field,
        "trace_id": trace_id,
    }
    if extra:
        error.update(extra)
    return {"error": error}
