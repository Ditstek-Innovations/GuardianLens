"""Request and response schemas — the API contract layer.

Every request model is ``extra="forbid"``: an unknown field is rejected,
never silently dropped (BACKEND_CODING_RULES 11). Server-owned fields —
reviewer_id, status, decided_at, tenant identity, audit metadata — do not
appear on any request model at all; their arrival is additionally caught
against the raw body by ReviewerAttributionGuard so the response is the
rule's 400 rather than a generic 422.

No response model exposes an ORM row directly, and no camera response
model has any field that could carry a stream URL.
"""
