"""Edge store — SQLite, DATABASE.md 11.

Durable buffer, not a system of record. The schema below is DATABASE.md 11.2
verbatim; the outbox state machine is 11.3; backpressure levels are 11.4.

Posture (DATABASE.md 11.1):
- journal_mode WAL — concurrent reader while the publisher writes;
- synchronous FULL — losing acknowledged events to a power cut would defeat
  the outbox's entire purpose;
- rows live until published and acknowledged, then row and evidence frame are
  reclaimed together.

What this store must never contain (DATABASE.md 11.5): video or audio in any
form, frames not attached to a candidate event, decrypted camera credentials
at rest, or any per-person identifier, embedding or track. Nothing in this
module writes any of those.
"""

from __future__ import annotations

import enum
import json
import logging
import os
import sqlite3
from dataclasses import dataclass
from pathlib import Path

__all__ = [
    "BackpressureLevel",
    "CounterKind",
    "EdgeStore",
    "OpenGap",
    "OutboxRow",
    "OutboxState",
]

logger = logging.getLogger(__name__)

# DATABASE.md 11.2 — SPECIFICATION, NOT A MIGRATION. SQLite 3, edge agent
# local store. Reproduced verbatim.
_SCHEMA = """
-- Unified outbox. Events, gaps and health share one delivery mechanism so
-- there is exactly one retry, ordering and backpressure implementation.
CREATE TABLE IF NOT EXISTS outbox (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,  -- delivery order
    kind            TEXT    NOT NULL
                    CHECK (kind IN ('event','coverage_gap','health')),
    idempotency_key TEXT    NOT NULL,   -- UUIDv7 for events; gap id for gaps
    payload         TEXT    NOT NULL,   -- canonical JSON
    evidence_path   TEXT,               -- local frame file, events only
    created_at      TEXT    NOT NULL,   -- ISO-8601 UTC, edge clock
    state           TEXT    NOT NULL DEFAULT 'pending'
                    CHECK (state IN ('pending','inflight','published','parked')),
    attempts        INTEGER NOT NULL DEFAULT 0,
    last_attempt_at TEXT,
    last_error      TEXT,
    UNIQUE (kind, idempotency_key)
);

CREATE INDEX IF NOT EXISTS idx_outbox_pending ON outbox (id) WHERE state = 'pending';
CREATE INDEX IF NOT EXISTS idx_outbox_parked  ON outbox (id) WHERE state = 'parked';

-- Applied configuration, so a restart does not lose it and an unreachable
-- control plane never causes a fallback to defaults (BR-001).
CREATE TABLE IF NOT EXISTS agent_config (
    id                  INTEGER PRIMARY KEY CHECK (id = 1),  -- single row
    config_version      INTEGER NOT NULL,
    document            TEXT    NOT NULL,   -- validated config JSON
    applied_at          TEXT    NOT NULL,
    last_fetch_at       TEXT,
    last_fetch_error    TEXT
);

-- Open coverage gaps, so a gap survives an agent restart.
CREATE TABLE IF NOT EXISTS open_gaps (
    gap_id      TEXT PRIMARY KEY,      -- UUID, generated here
    camera_id   TEXT,                  -- NULL for agent-scope gaps
    reason      TEXT NOT NULL,
    started_at  TEXT NOT NULL
);

-- Suppression counters. BR-D-02: a discarded detection is counted,
-- never silently dropped. Aggregated, never per-person.
CREATE TABLE IF NOT EXISTS detection_counters (
    bucket_start        TEXT NOT NULL,   -- hour bucket, ISO-8601 UTC
    camera_id           TEXT NOT NULL,
    rule_id             TEXT,
    below_threshold     INTEGER NOT NULL DEFAULT 0,
    outside_zone        INTEGER NOT NULL DEFAULT 0,
    debounce_suppressed INTEGER NOT NULL DEFAULT 0,
    dwell_unmet         INTEGER NOT NULL DEFAULT 0,
    context_unmet       INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (bucket_start, camera_id, rule_id)
);
"""


class OutboxState(str, enum.Enum):
    """DATABASE.md 11.3."""

    PENDING = "pending"
    INFLIGHT = "inflight"
    PUBLISHED = "published"
    PARKED = "parked"


class OutboxKind(str, enum.Enum):
    EVENT = "event"
    COVERAGE_GAP = "coverage_gap"
    HEALTH = "health"


class CounterKind(str, enum.Enum):
    """The four suppression counters of DATABASE.md 11.2 (BR-D-02)."""

    BELOW_THRESHOLD = "below_threshold"
    OUTSIDE_ZONE = "outside_zone"
    DEBOUNCE_SUPPRESSED = "debounce_suppressed"
    DWELL_UNMET = "dwell_unmet"
    #: The rule required the condition to be attached to a person and the
    #: frame's geometry did not support it (held-vs-lying discriminator).
    CONTEXT_UNMET = "context_unmet"


class BackpressureLevel(enum.Enum):
    """DATABASE.md 11.4 thresholds."""

    NORMAL = "normal"
    WARNING = "warning"
    CRITICAL = "critical"


# One constant statement per counter. Column names never come from data, so
# there is no string-built SQL at call time.
_COUNTER_SQL = {
    CounterKind.BELOW_THRESHOLD: (
        "INSERT INTO detection_counters"
        " (bucket_start, camera_id, rule_id, below_threshold)"
        " VALUES (?, ?, ?, 1)"
        " ON CONFLICT(bucket_start, camera_id, rule_id)"
        " DO UPDATE SET below_threshold = below_threshold + 1"
    ),
    CounterKind.OUTSIDE_ZONE: (
        "INSERT INTO detection_counters"
        " (bucket_start, camera_id, rule_id, outside_zone)"
        " VALUES (?, ?, ?, 1)"
        " ON CONFLICT(bucket_start, camera_id, rule_id)"
        " DO UPDATE SET outside_zone = outside_zone + 1"
    ),
    CounterKind.DEBOUNCE_SUPPRESSED: (
        "INSERT INTO detection_counters"
        " (bucket_start, camera_id, rule_id, debounce_suppressed)"
        " VALUES (?, ?, ?, 1)"
        " ON CONFLICT(bucket_start, camera_id, rule_id)"
        " DO UPDATE SET debounce_suppressed = debounce_suppressed + 1"
    ),
    CounterKind.DWELL_UNMET: (
        "INSERT INTO detection_counters"
        " (bucket_start, camera_id, rule_id, dwell_unmet)"
        " VALUES (?, ?, ?, 1)"
        " ON CONFLICT(bucket_start, camera_id, rule_id)"
        " DO UPDATE SET dwell_unmet = dwell_unmet + 1"
    ),
    CounterKind.CONTEXT_UNMET: (
        "INSERT INTO detection_counters"
        " (bucket_start, camera_id, rule_id, context_unmet)"
        " VALUES (?, ?, ?, 1)"
        " ON CONFLICT(bucket_start, camera_id, rule_id)"
        " DO UPDATE SET context_unmet = context_unmet + 1"
    ),
}


@dataclass(frozen=True)
class OutboxRow:
    id: int
    kind: str
    idempotency_key: str
    payload: dict
    evidence_path: str | None
    created_at: str
    state: str
    attempts: int
    last_error: str | None


@dataclass(frozen=True)
class OpenGap:
    gap_id: str
    camera_id: str | None
    reason: str
    started_at: str


@dataclass(frozen=True)
class AppliedConfigRow:
    config_version: int
    document: dict
    applied_at: str
    last_fetch_at: str | None
    last_fetch_error: str | None


class EdgeStore:
    """Typed access to the edge SQLite store.

    ``warning_bytes`` / ``critical_bytes`` are the DATABASE.md 11.4
    backpressure thresholds. They are required constructor parameters with
    **no default**, deliberately: the values are `[OPEN — PRD OQ-4]` — they
    cannot be set before candidate volume per shift is measured in pilot, and
    BACKEND_CODING_RULES 4 forbids resolving an `[OPEN]` requirement by
    assumption. The deployment configuration must state them explicitly.
    """

    def __init__(
        self,
        db_path: str | os.PathLike[str],
        *,
        warning_bytes: int,
        critical_bytes: int,
    ) -> None:
        if warning_bytes <= 0 or critical_bytes <= 0:
            raise ValueError("backpressure thresholds must be positive")
        if critical_bytes < warning_bytes:
            raise ValueError("critical threshold must be >= warning threshold")
        self._db_path = Path(db_path)
        self._warning_bytes = warning_bytes
        self._critical_bytes = critical_bytes
        self._conn = sqlite3.connect(self._db_path)
        self._conn.row_factory = sqlite3.Row
        # DATABASE.md 11.1 / 11.2 pragmas.
        self._conn.execute("PRAGMA journal_mode = WAL")
        self._conn.execute("PRAGMA synchronous = FULL")
        self._conn.execute("PRAGMA foreign_keys = ON")
        with self._conn:
            self._conn.executescript(_SCHEMA)
            # Additive store evolution: a DB created before context_unmet
            # existed gains the column in place (CREATE IF NOT EXISTS does
            # not alter an existing table).
            columns = {
                row[1]
                for row in self._conn.execute(
                    "PRAGMA table_info(detection_counters)"
                )
            }
            if "context_unmet" not in columns:
                self._conn.execute(
                    "ALTER TABLE detection_counters"
                    " ADD COLUMN context_unmet INTEGER NOT NULL DEFAULT 0"
                )

    def close(self) -> None:
        self._conn.close()

    # ------------------------------------------------------------------
    # Outbox — enqueue
    # ------------------------------------------------------------------

    def enqueue_event(
        self,
        payload: dict,
        evidence_path: str | None,
        idempotency_key: str,
        *,
        created_at: str,
    ) -> int:
        return self._enqueue(
            OutboxKind.EVENT, payload, evidence_path, idempotency_key, created_at
        )

    def enqueue_gap(
        self, payload: dict, idempotency_key: str, *, created_at: str
    ) -> int:
        return self._enqueue(
            OutboxKind.COVERAGE_GAP, payload, None, idempotency_key, created_at
        )

    def enqueue_health(
        self, payload: dict, idempotency_key: str, *, created_at: str
    ) -> int:
        return self._enqueue(
            OutboxKind.HEALTH, payload, None, idempotency_key, created_at
        )

    def _enqueue(
        self,
        kind: OutboxKind,
        payload: dict,
        evidence_path: str | None,
        idempotency_key: str,
        created_at: str,
    ) -> int:
        with self._conn:
            cursor = self._conn.execute(
                "INSERT INTO outbox"
                " (kind, idempotency_key, payload, evidence_path, created_at)"
                " VALUES (?, ?, ?, ?, ?)",
                (
                    kind.value,
                    idempotency_key,
                    json.dumps(payload, sort_keys=True, separators=(",", ":")),
                    evidence_path,
                    created_at,
                ),
            )
        row_id = cursor.lastrowid
        if row_id is None:  # pragma: no cover - sqlite always sets it here
            raise RuntimeError("outbox insert returned no row id")
        return row_id

    # ------------------------------------------------------------------
    # Outbox — state machine (DATABASE.md 11.3)
    # ------------------------------------------------------------------

    def claim_batch(self, limit: int, *, now: str) -> list[OutboxRow]:
        """Claim the oldest pending rows, kind-agnostic, and mark inflight.

        Oldest ``id`` first: AUTOINCREMENT gives strict delivery ordering,
        and a reviewer needs chronological context after an outage
        (ARCHITECTURE.md 6.2).
        """
        with self._conn:
            rows = self._conn.execute(
                "SELECT * FROM outbox WHERE state = 'pending'"
                " ORDER BY id ASC LIMIT ?",
                (limit,),
            ).fetchall()
            ids = [row["id"] for row in rows]
            self._conn.executemany(
                "UPDATE outbox SET state = 'inflight', last_attempt_at = ?"
                " WHERE id = ?",
                [(now, row_id) for row_id in ids],
            )
        return [self._to_row(row, state=OutboxState.INFLIGHT.value) for row in rows]

    def mark_published(self, row_id: int) -> None:
        """201, or 200 meaning already present — both are success.

        Row and local frame are reclaimed together (DATABASE.md 11.3): the
        publish acknowledgement covers the evidence, which travels inside the
        event payload (TRD 10.3), so nothing else references the file.
        """
        row = self._conn.execute(
            "SELECT evidence_path FROM outbox WHERE id = ?", (row_id,)
        ).fetchone()
        with self._conn:
            self._conn.execute(
                "UPDATE outbox SET state = 'published' WHERE id = ?", (row_id,)
            )
            self._conn.execute("DELETE FROM outbox WHERE id = ?", (row_id,))
        if row is not None and row["evidence_path"]:
            Path(row["evidence_path"]).unlink(missing_ok=True)

    def mark_retry(self, row_id: int, error: str, *, now: str) -> None:
        """5xx / timeout / connection failure → back to pending.

        Retries are unlimited (TRD 5.6): the outbox exists precisely so a
        partition never loses an event.
        """
        with self._conn:
            self._conn.execute(
                "UPDATE outbox SET state = 'pending', attempts = attempts + 1,"
                " last_attempt_at = ?, last_error = ? WHERE id = ?",
                (now, error, row_id),
            )

    def release_claim(self, row_id: int) -> None:
        """Return a claimed-but-never-attempted row to pending.

        Used when a tick aborts mid-batch (backoff after a retryable
        failure): the remaining claimed rows were not sent, so no attempt is
        counted against them and no error is recorded.
        """
        with self._conn:
            self._conn.execute(
                "UPDATE outbox SET state = 'pending' WHERE id = ?"
                " AND state = 'inflight'",
                (row_id,),
            )

    def park(self, row_id: int, error: str, *, now: str) -> None:
        """Permanently invalid payload → parked, terminal.

        Never retried, never auto-deleted: a parked row is a defect, and
        defects must not disappear quietly (DATABASE.md 11.3). Operator
        action only.
        """
        with self._conn:
            self._conn.execute(
                "UPDATE outbox SET state = 'parked', attempts = attempts + 1,"
                " last_attempt_at = ?, last_error = ? WHERE id = ?",
                (now, error, row_id),
            )
        logger.error(
            "outbox row parked as permanently invalid: id=%s error=%s",
            row_id,
            error,
        )

    def pending_count(self) -> int:
        row = self._conn.execute(
            "SELECT COUNT(*) AS n FROM outbox WHERE state = 'pending'"
        ).fetchone()
        return int(row["n"])

    def parked_rows(self) -> list[OutboxRow]:
        rows = self._conn.execute(
            "SELECT * FROM outbox WHERE state = 'parked' ORDER BY id ASC"
        ).fetchall()
        return [self._to_row(row) for row in rows]

    def _to_row(self, row: sqlite3.Row, *, state: str | None = None) -> OutboxRow:
        return OutboxRow(
            id=row["id"],
            kind=row["kind"],
            idempotency_key=row["idempotency_key"],
            payload=json.loads(row["payload"]),
            evidence_path=row["evidence_path"],
            created_at=row["created_at"],
            state=state if state is not None else row["state"],
            attempts=row["attempts"],
            last_error=row["last_error"],
        )

    # ------------------------------------------------------------------
    # Coverage gaps — survive restart (DATABASE.md 11.2 open_gaps)
    # ------------------------------------------------------------------

    def open_gap(
        self, gap_id: str, camera_id: str | None, reason: str, started_at: str
    ) -> None:
        with self._conn:
            self._conn.execute(
                "INSERT INTO open_gaps (gap_id, camera_id, reason, started_at)"
                " VALUES (?, ?, ?, ?)",
                (gap_id, camera_id, reason, started_at),
            )

    def close_gap(self, gap_id: str) -> None:
        with self._conn:
            self._conn.execute(
                "DELETE FROM open_gaps WHERE gap_id = ?", (gap_id,)
            )

    def open_gaps(self) -> list[OpenGap]:
        rows = self._conn.execute(
            "SELECT * FROM open_gaps ORDER BY started_at ASC, gap_id ASC"
        ).fetchall()
        return [
            OpenGap(
                gap_id=row["gap_id"],
                camera_id=row["camera_id"],
                reason=row["reason"],
                started_at=row["started_at"],
            )
            for row in rows
        ]

    # ------------------------------------------------------------------
    # Suppression counters (BR-D-02)
    # ------------------------------------------------------------------

    def increment_counter(
        self,
        bucket_start: str,
        camera_id: str,
        rule_id: str | None,
        counter: CounterKind,
    ) -> None:
        with self._conn:
            self._conn.execute(
                _COUNTER_SQL[counter], (bucket_start, camera_id, rule_id)
            )

    def counters(self) -> list[dict]:
        rows = self._conn.execute(
            "SELECT * FROM detection_counters"
            " ORDER BY bucket_start, camera_id, rule_id"
        ).fetchall()
        return [dict(row) for row in rows]

    # ------------------------------------------------------------------
    # Applied configuration (BR-001: last-known-good, never defaults)
    # ------------------------------------------------------------------

    def save_config(
        self, config_version: int, document: dict, *, applied_at: str
    ) -> None:
        """Persist the validated configuration document atomically."""
        with self._conn:
            self._conn.execute(
                "INSERT INTO agent_config"
                " (id, config_version, document, applied_at, last_fetch_at,"
                "  last_fetch_error)"
                " VALUES (1, ?, ?, ?, ?, NULL)"
                " ON CONFLICT(id) DO UPDATE SET"
                "  config_version = excluded.config_version,"
                "  document = excluded.document,"
                "  applied_at = excluded.applied_at,"
                "  last_fetch_at = excluded.last_fetch_at,"
                "  last_fetch_error = NULL",
                (
                    config_version,
                    json.dumps(document, sort_keys=True, separators=(",", ":")),
                    applied_at,
                    applied_at,
                ),
            )

    def record_fetch_result(self, *, fetched_at: str, error: str | None) -> None:
        """Record a fetch outcome without touching the applied document."""
        with self._conn:
            self._conn.execute(
                "UPDATE agent_config SET last_fetch_at = ?, last_fetch_error = ?"
                " WHERE id = 1",
                (fetched_at, error),
            )

    def load_config(self) -> AppliedConfigRow | None:
        row = self._conn.execute(
            "SELECT * FROM agent_config WHERE id = 1"
        ).fetchone()
        if row is None:
            return None
        return AppliedConfigRow(
            config_version=row["config_version"],
            document=json.loads(row["document"]),
            applied_at=row["applied_at"],
            last_fetch_at=row["last_fetch_at"],
            last_fetch_error=row["last_fetch_error"],
        )

    # ------------------------------------------------------------------
    # Backpressure (DATABASE.md 11.4)
    # ------------------------------------------------------------------

    def usage_bytes(self) -> int:
        """Bytes held by undelivered outbox rows and their evidence frames.

        Counts payload bytes for rows not yet reclaimed plus the size of
        every referenced evidence file still on disk. This is the quantity
        the disk cap protects, and it is what publishing reclaims.
        """
        total = 0
        rows = self._conn.execute(
            "SELECT payload, evidence_path FROM outbox"
            " WHERE state IN ('pending','inflight','parked')"
        ).fetchall()
        for row in rows:
            total += len(row["payload"].encode("utf-8"))
            evidence_path = row["evidence_path"]
            if evidence_path:
                path = Path(evidence_path)
                if path.exists():
                    total += path.stat().st_size
        return total

    def backpressure_level(self) -> BackpressureLevel:
        usage = self.usage_bytes()
        if usage >= self._critical_bytes:
            return BackpressureLevel.CRITICAL
        if usage >= self._warning_bytes:
            return BackpressureLevel.WARNING
        return BackpressureLevel.NORMAL
