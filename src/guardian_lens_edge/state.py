"""ADR-009: one explicit agent operating-state machine.

States and transitions are ARCHITECTURE.md 6.6 (RS-6):

    Starting -> Halted    model artefact missing or hash mismatch
    Starting -> Healthy   model loaded + warmed
    Healthy  -> Degraded  transient inference failures cross rate threshold
    Degraded -> Healthy   failure rate recovers
    Degraded -> Halted    sustained failure OR outbox critical
    Healthy  -> Halted    outbox critical (DATABASE.md 11.4 / RS-2 — the
                          disk cap halts generation regardless of inference
                          health; 6.6 draws the edge from Degraded only
                          because RS-6 is the inference scenario)
    Halted   -> Healthy   operator intervention + successful restart, or —
                          for reason='outbox_full' only — backlog drained
                          below the warning level (DATABASE.md 11.4)

Every module reports conditions INTO this machine; no module decides
independently whether to keep emitting. Entering Halted always opens a
coverage gap for every affected camera and raises a CRITICAL log —
a halted agent is loud, never silent.

Failure-rate thresholds are `[OPEN]` (ADR-009: set from pilot data), so they
are required constructor parameters with no default.
"""

from __future__ import annotations

import enum
import logging
import uuid
from collections import deque
from datetime import datetime

from guardian_lens_edge.store import BackpressureLevel, EdgeStore, OpenGap

__all__ = [
    "AgentStateMachine",
    "GapRecorder",
    "HaltReason",
    "OperatingState",
    "STREAM_LOST_REASON",
]

logger = logging.getLogger(__name__)

#: RS-5 gap reason recorded by MOD-1 on connection loss (ARCHITECTURE.md
#: 6.5). Not a HaltReason: a lost stream is a per-camera condition and
#: does not stop the agent.
STREAM_LOST_REASON = "stream_lost"


class OperatingState(str, enum.Enum):
    STARTING = "starting"
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    HALTED = "halted"


class HaltReason(str, enum.Enum):
    MODEL_LOAD_FAILED = "model_load_failed"
    SUSTAINED_INFERENCE_FAILURE = "sustained_inference_failure"
    OUTBOX_FULL = "outbox_full"


def _iso(instant: datetime) -> str:
    if instant.tzinfo is None:
        raise ValueError("timestamps must be timezone-aware")
    return instant.isoformat(timespec="seconds")


class GapRecorder:
    """The RS-5 gap mechanics, in exactly one place.

    Opening a gap persists it to ``open_gaps`` (so it survives restart) AND
    enqueues the outbox record with ``ended_at`` null; closing removes the
    row and enqueues the same gap id with ``ended_at`` set, which the
    ingest upserts idempotently (ARCHITECTURE.md 6.5). Shared by the
    ADR-009 state machine (halt gaps) and the MOD-1 stream wiring
    (``stream_lost`` gaps) so the wire shape and idempotency keys cannot
    drift between producers.
    """

    def __init__(self, store: EdgeStore) -> None:
        self._store = store

    def open(
        self, camera_id: str | None, reason: str, now: datetime
    ) -> str:
        """Open and enqueue one gap; returns the generated gap id."""
        gap_id = str(uuid.uuid4())
        started_at = _iso(now)
        self._store.open_gap(gap_id, camera_id, reason, started_at)
        self._store.enqueue_gap(
            {
                # `id`, not `gap_id`: the wire name is the DATABASE.md 5.7
                # column name, and the ingest schema forbids extras.
                "id": gap_id,
                "camera_id": camera_id,
                "reason": reason,
                "started_at": started_at,
                "ended_at": None,
            },
            idempotency_key=gap_id,
            created_at=started_at,
        )
        return gap_id

    def close(self, gap: OpenGap, now: datetime) -> None:
        self._store.close_gap(gap.gap_id)
        self._store.enqueue_gap(
            {
                "id": gap.gap_id,
                "camera_id": gap.camera_id,
                "reason": gap.reason,
                "started_at": gap.started_at,
                "ended_at": _iso(now),
            },
            idempotency_key=f"{gap.gap_id}:closed",
            created_at=_iso(now),
        )
        logger.info(
            "coverage gap closed: gap_id=%s reason=%s", gap.gap_id, gap.reason
        )

    def open_for(
        self, camera_id: str | None, reason: str
    ) -> list[OpenGap]:
        """The currently open gaps matching camera and reason."""
        return [
            gap
            for gap in self._store.open_gaps()
            if gap.camera_id == camera_id and gap.reason == reason
        ]

    def close_matching(self, reasons: set[str], now: datetime) -> None:
        """Close every open gap whose reason is in ``reasons``."""
        for gap in self._store.open_gaps():
            if gap.reason in reasons:
                self.close(gap, now)


class AgentStateMachine:
    """The single authority on whether the agent may generate candidates.

    All methods take ``now`` explicitly — the machine never reads a wall
    clock, so tests and the replaying dev agent drive it deterministically.

    ``failure_window`` / ``degraded_failure_rate`` / ``halt_failure_rate``
    are `[OPEN]` per ADR-009 and therefore mandatory: rates are evaluated
    over the most recent ``failure_window`` inference outcomes, and only
    once the window is full, so a single startup hiccup cannot flap the
    state.
    """

    def __init__(
        self,
        store: EdgeStore,
        *,
        failure_window: int,
        degraded_failure_rate: float,
        halt_failure_rate: float,
    ) -> None:
        if failure_window <= 0:
            raise ValueError("failure_window must be positive")
        if not 0.0 < degraded_failure_rate <= halt_failure_rate <= 1.0:
            raise ValueError(
                "require 0 < degraded_failure_rate <= halt_failure_rate <= 1"
            )
        self._store = store
        self._gaps = GapRecorder(store)
        self._failure_window = failure_window
        self._degraded_failure_rate = degraded_failure_rate
        self._halt_failure_rate = halt_failure_rate
        self._state = OperatingState.STARTING
        self._halt_reason: HaltReason | None = None
        self._camera_ids: list[str] = []
        self._outcomes: deque[bool] = deque(maxlen=failure_window)

    @property
    def state(self) -> OperatingState:
        return self._state

    @property
    def halt_reason(self) -> HaltReason | None:
        return self._halt_reason

    def can_generate(self) -> bool:
        """Degraded still emits events (RS-6); Halted emits none."""
        return self._state in (OperatingState.HEALTHY, OperatingState.DEGRADED)

    def set_cameras(self, camera_ids: list[str]) -> None:
        self._camera_ids = list(camera_ids)

    # ------------------------------------------------------------------
    # Conditions reported in by modules
    # ------------------------------------------------------------------

    def report_model_loaded(self, now: datetime) -> None:
        """Starting → Healthy. Also closes halt gaps after an operator
        restart (RS-6: Halted → Healthy requires a successful restart, which
        lands here as a fresh process reporting its model loaded)."""
        if self._state is not OperatingState.STARTING:
            return
        self._transition(OperatingState.HEALTHY, now)
        self._gaps.close_matching(
            {
                HaltReason.MODEL_LOAD_FAILED.value,
                HaltReason.SUSTAINED_INFERENCE_FAILURE.value,
            },
            now,
        )

    def report_model_load_failed(self, now: datetime) -> None:
        """Starting → Halted: never run without a model, never silently
        produce zero detections (TRD 5.6)."""
        if self._state is not OperatingState.STARTING:
            return
        self._enter_halted(HaltReason.MODEL_LOAD_FAILED, now)

    def report_inference_success(self, now: datetime) -> None:
        self._outcomes.append(False)
        self._evaluate_failure_rate(now)

    def report_inference_failure(self, now: datetime) -> None:
        self._outcomes.append(True)
        self._evaluate_failure_rate(now)

    def report_outbox_level(
        self, level: BackpressureLevel, now: datetime
    ) -> None:
        """DATABASE.md 11.4: warning alerts; critical halts; drained below
        warning closes the gap and resumes."""
        if level is BackpressureLevel.WARNING:
            logger.warning("outbox backlog growing: usage above warning threshold")
            return
        if level is BackpressureLevel.CRITICAL:
            if self._state in (OperatingState.HEALTHY, OperatingState.DEGRADED):
                self._enter_halted(HaltReason.OUTBOX_FULL, now)
            return
        # level NORMAL — below the warning threshold.
        self._gaps.close_matching({HaltReason.OUTBOX_FULL.value}, now)
        if (
            self._state is OperatingState.HALTED
            and self._halt_reason is HaltReason.OUTBOX_FULL
        ):
            self._halt_reason = None
            self._transition(OperatingState.HEALTHY, now)
            logger.info("outbox drained below warning level; generation resumed")

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _evaluate_failure_rate(self, now: datetime) -> None:
        if len(self._outcomes) < self._failure_window:
            return
        rate = sum(self._outcomes) / len(self._outcomes)
        if self._state is OperatingState.HEALTHY:
            if rate >= self._degraded_failure_rate:
                self._transition(OperatingState.DEGRADED, now)
                logger.warning(
                    "inference failure rate %.2f crossed degraded threshold", rate
                )
        elif self._state is OperatingState.DEGRADED:
            if rate >= self._halt_failure_rate:
                # Sustained failure: fewer events over wrong events (BR-012).
                self._enter_halted(HaltReason.SUSTAINED_INFERENCE_FAILURE, now)
            elif rate < self._degraded_failure_rate:
                self._transition(OperatingState.HEALTHY, now)
                logger.info("inference failure rate recovered: %.2f", rate)

    def _transition(self, new_state: OperatingState, now: datetime) -> None:
        old = self._state
        self._state = new_state
        logger.info(
            "agent state transition: %s -> %s at %s",
            old.value,
            new_state.value,
            _iso(now),
        )

    def _enter_halted(self, reason: HaltReason, now: datetime) -> None:
        self._halt_reason = reason
        self._transition(OperatingState.HALTED, now)
        # ADR-009: entering Halted ALWAYS opens a coverage gap for every
        # affected camera and raises a critical alert. With no cameras
        # configured, one agent-scope gap (camera_id NULL) is opened so the
        # halt is never invisible.
        affected: list[str | None] = list(self._camera_ids) or [None]
        for camera_id in affected:
            self._gaps.open(camera_id, reason.value, now)
        logger.critical(
            "agent HALTED: reason=%s cameras=%s — detection stopped, "
            "coverage gap(s) open",
            reason.value,
            [camera_id or "agent-scope" for camera_id in affected],
        )

