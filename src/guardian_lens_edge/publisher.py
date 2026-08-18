"""Outbox publisher — IF-E5, the edge side of RS-2.

Drains the unified outbox oldest-first (chronological context for the
reviewer after an outage, ARCHITECTURE.md 6.2) and applies the DATABASE.md
11.3 state machine to every delivery outcome:

    201                        -> published (row + frame reclaimed)
    200                        -> published — the receiver deduplicated; the
                                  event exists exactly once; logged at debug
    401                        -> re-authenticate once, then retry the send;
                                  a second 401 is retried later, not parked —
                                  an auth outage is transient, the payload
                                  is not invalid
    408 / 5xx / network error  -> back to pending; backoff 1s, 2s, 4s …
                                  capped at 60s; unlimited retries (TRD 5.6)
    422                        -> parked, ERROR log — the payload will never
                                  become valid; retrying forever would block
                                  the queue behind a poison row
    other 4xx                  -> parked

TRD 10.3 defines ``POST /api/v1/events`` as a single-event request — there
is no batch envelope in the contract — so a claimed batch is drained as one
request per row, in id order.
"""

from __future__ import annotations

import base64
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path

import httpx

from guardian_lens_edge.auth import AgentAuthenticator, AgentAuthError
from guardian_lens_edge.store import EdgeStore, OutboxRow

__all__ = ["Publisher", "PublishReport"]

logger = logging.getLogger(__name__)

_ROUTES = {
    "event": "/api/v1/events",
    "coverage_gap": "/api/v1/coverage-gaps",
    "health": "/api/v1/agents/health",
}
_RETRYABLE_STATUS_MIN = 500
_STATUS_REQUEST_TIMEOUT = 408


@dataclass
class PublishReport:
    published: int = 0
    retried: int = 0
    parked: int = 0
    released: int = 0
    errors: list[str] = field(default_factory=list)


class Publisher:
    """Drains the outbox through an injected ``httpx.Client``.

    ``tick(now)`` is steppable and never sleeps: after a retryable failure
    it records when the next attempt is due and refuses to send until then.
    """

    def __init__(
        self,
        store: EdgeStore,
        client: httpx.Client,
        api_base: str,
        authenticator: AgentAuthenticator,
        *,
        batch_size: int = 25,
        backoff_base_seconds: float = 1.0,
        backoff_cap_seconds: float = 60.0,
    ) -> None:
        if batch_size <= 0:
            raise ValueError("batch_size must be positive")
        self._store = store
        self._client = client
        self._api_base = api_base.rstrip("/")
        self._auth = authenticator
        self._batch_size = batch_size
        self._backoff_base = backoff_base_seconds
        self._backoff_cap = backoff_cap_seconds
        self._next_attempt_at: datetime | None = None

    @property
    def next_attempt_at(self) -> datetime | None:
        return self._next_attempt_at

    def tick(self, now: datetime) -> PublishReport:
        report = PublishReport()
        if self._next_attempt_at is not None and now < self._next_attempt_at:
            return report
        batch = self._store.claim_batch(
            self._batch_size, now=now.isoformat(timespec="seconds")
        )
        for index, row in enumerate(batch):
            outcome = self._send_row(row, now, report)
            if outcome == "stop":
                # Release the rest of the claim untouched: they were never
                # attempted, so no attempt is counted against them.
                for remaining in batch[index + 1:]:
                    self._store.release_claim(remaining.id)
                    report.released += 1
                return report
        return report

    # ------------------------------------------------------------------

    def _send_row(
        self, row: OutboxRow, now: datetime, report: PublishReport
    ) -> str:
        """Returns 'continue' to keep draining or 'stop' to end the tick."""
        try:
            payload = self._request_payload(row)
        except FileNotFoundError:
            # The spooled evidence frame is gone: the payload can never be
            # delivered complete, and evidence presence is a precondition of
            # a decision (ADR-013). Park it as the defect it is.
            self._store.park(
                row.id,
                "evidence file missing from spool",
                now=now.isoformat(timespec="seconds"),
            )
            report.parked += 1
            return "continue"

        try:
            response = self._post(row, payload)
            if response.status_code == 401:
                # Token expired: re-authenticate once and retry the send.
                self._auth.invalidate()
                response = self._post(row, payload)
        except (httpx.HTTPError, AgentAuthError) as exc:
            self._retry(row, f"{type(exc).__name__}: {exc}", now, report)
            return "stop"

        status = response.status_code
        if status == 201:
            self._store.mark_published(row.id)
            report.published += 1
            self._next_attempt_at = None
            return "continue"
        if status == 200:
            # Success: the receiver already has it, deduplicated by the
            # idempotency key. Exactly-once at the record, not the wire.
            logger.debug(
                "outbox row already present at receiver: kind=%s key=%s",
                row.kind,
                row.idempotency_key,
            )
            self._store.mark_published(row.id)
            report.published += 1
            self._next_attempt_at = None
            return "continue"
        if status == _STATUS_REQUEST_TIMEOUT or status >= _RETRYABLE_STATUS_MIN:
            self._retry(row, f"HTTP {status}", now, report)
            return "stop"
        if status == 401:
            # Still unauthorised after one re-auth: an auth-plane problem,
            # not a payload problem. Retry later rather than park.
            self._retry(row, "HTTP 401 after re-authentication", now, report)
            return "stop"
        if status == 422:
            logger.error(
                "payload permanently invalid (422): kind=%s key=%s body=%s",
                row.kind,
                row.idempotency_key,
                response.text[:500],
            )
            self._store.park(
                row.id, f"HTTP 422: {response.text[:500]}",
                now=now.isoformat(timespec="seconds"),
            )
            report.parked += 1
            return "continue"
        # Any other 4xx: the request is wrong in a way retrying cannot fix.
        self._store.park(
            row.id, f"HTTP {status}", now=now.isoformat(timespec="seconds")
        )
        report.parked += 1
        return "continue"

    def _post(self, row: OutboxRow, payload: dict) -> httpx.Response:
        return self._client.post(
            f"{self._api_base}{_ROUTES[row.kind]}",
            json=payload,
            headers=self._auth.bearer_header(),
        )

    def _request_payload(self, row: OutboxRow) -> dict:
        payload = dict(row.payload)
        if row.kind == "event" and row.evidence_path:
            frame_bytes = Path(row.evidence_path).read_bytes()
            evidence = dict(payload.get("evidence") or {})
            evidence["data_b64"] = base64.b64encode(frame_bytes).decode("ascii")
            payload["evidence"] = evidence
        return payload

    def _retry(
        self, row: OutboxRow, error: str, now: datetime, report: PublishReport
    ) -> None:
        self._store.mark_retry(
            row.id, error, now=now.isoformat(timespec="seconds")
        )
        # row.attempts is the count BEFORE this failure: first failure backs
        # off 1s, then 2s, 4s ... capped at 60s (TRD 5.6). Unlimited.
        delay = min(self._backoff_cap, self._backoff_base * (2 ** row.attempts))
        self._next_attempt_at = now + timedelta(seconds=delay)
        report.retried += 1
        report.errors.append(error)
        logger.warning(
            "delivery failed, will retry: kind=%s key=%s attempts=%s "
            "next_in=%.0fs error=%s",
            row.kind,
            row.idempotency_key,
            row.attempts + 1,
            delay,
            error,
        )
