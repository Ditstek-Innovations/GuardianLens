"""ADR-009 operating-state machine — every legal transition, and Halted is loud."""

from __future__ import annotations

import pytest

from guardian_lens_edge.state import (
    AgentStateMachine,
    HaltReason,
    OperatingState,
)
from guardian_lens_edge.store import BackpressureLevel, EdgeStore

from tests.edge.conftest import CAMERA_ID, at


def make_machine(store: EdgeStore, **kwargs) -> AgentStateMachine:
    params = {
        # [OPEN] thresholds per ADR-009: tests pick explicit values.
        "failure_window": 4,
        "degraded_failure_rate": 0.5,
        "halt_failure_rate": 0.75,
    }
    params.update(kwargs)
    machine = AgentStateMachine(store, **params)
    machine.set_cameras([CAMERA_ID])
    return machine


def gap_reasons(store: EdgeStore) -> list[str]:
    return [gap.reason for gap in store.open_gaps()]


def test_starting_cannot_generate(store: EdgeStore) -> None:
    machine = make_machine(store)
    assert machine.state is OperatingState.STARTING
    assert machine.can_generate() is False


def test_starting_to_healthy_on_model_loaded(store: EdgeStore) -> None:
    machine = make_machine(store)
    machine.report_model_loaded(at(0))
    assert machine.state is OperatingState.HEALTHY
    assert machine.can_generate() is True


def test_starting_to_halted_on_model_load_failure_is_loud(
    store: EdgeStore, caplog
) -> None:
    machine = make_machine(store)
    with caplog.at_level("CRITICAL", logger="guardian_lens_edge.state"):
        machine.report_model_load_failed(at(0))
    assert machine.state is OperatingState.HALTED
    assert machine.halt_reason is HaltReason.MODEL_LOAD_FAILED
    assert machine.can_generate() is False
    # Loud: a persisted open gap per camera, a gap record in the outbox,
    # and a CRITICAL log line.
    assert gap_reasons(store) == ["model_load_failed"]
    batch = store.claim_batch(10, now="2026-08-12T09:00:00+00:00")
    assert [row.kind for row in batch] == ["coverage_gap"]
    assert batch[0].payload["camera_id"] == CAMERA_ID
    assert batch[0].payload["ended_at"] is None
    assert any(record.levelname == "CRITICAL" for record in caplog.records)


def test_halt_with_no_cameras_opens_agent_scope_gap(store: EdgeStore) -> None:
    machine = AgentStateMachine(
        store,
        failure_window=4,
        degraded_failure_rate=0.5,
        halt_failure_rate=0.75,
    )
    machine.report_model_load_failed(at(0))
    gaps = store.open_gaps()
    assert len(gaps) == 1
    assert gaps[0].camera_id is None


def test_healthy_to_degraded_on_failure_rate(store: EdgeStore) -> None:
    machine = make_machine(store)
    machine.report_model_loaded(at(0))
    machine.report_inference_success(at(1))
    machine.report_inference_success(at(2))
    machine.report_inference_failure(at(3))
    assert machine.state is OperatingState.HEALTHY  # window not yet full
    machine.report_inference_failure(at(4))
    # Window [S, S, F, F] -> rate 0.5 >= degraded threshold.
    assert machine.state is OperatingState.DEGRADED
    assert machine.can_generate() is True  # Degraded still emits (RS-6)


def test_degraded_recovers_to_healthy(store: EdgeStore) -> None:
    machine = make_machine(store)
    machine.report_model_loaded(at(0))
    for second in range(2):
        machine.report_inference_failure(at(second))
    for second in range(2, 4):
        machine.report_inference_success(at(second))
    assert machine.state is OperatingState.DEGRADED
    # Successes push the failure rate below the threshold.
    machine.report_inference_success(at(4))
    assert machine.state is OperatingState.HEALTHY


def test_degraded_to_halted_on_sustained_failure(
    store: EdgeStore, caplog
) -> None:
    machine = make_machine(store)
    machine.report_model_loaded(at(0))
    with caplog.at_level("CRITICAL", logger="guardian_lens_edge.state"):
        # Sample 4 fills the window (rate 1.0 -> Degraded); sample 5 finds
        # the rate still at the halt threshold while Degraded -> Halted.
        for second in range(5):
            machine.report_inference_failure(at(second))
    assert machine.state is OperatingState.HALTED
    assert machine.halt_reason is HaltReason.SUSTAINED_INFERENCE_FAILURE
    assert gap_reasons(store) == ["sustained_inference_failure"]
    assert any(record.levelname == "CRITICAL" for record in caplog.records)


def test_outbox_critical_halts_with_outbox_full(store: EdgeStore) -> None:
    machine = make_machine(store)
    machine.report_model_loaded(at(0))
    machine.report_outbox_level(BackpressureLevel.CRITICAL, at(1))
    assert machine.state is OperatingState.HALTED
    assert machine.halt_reason is HaltReason.OUTBOX_FULL
    assert gap_reasons(store) == ["outbox_full"]


def test_outbox_critical_halts_from_degraded_too(store: EdgeStore) -> None:
    machine = make_machine(store)
    machine.report_model_loaded(at(0))
    machine.report_inference_failure(at(1))
    machine.report_inference_failure(at(2))
    machine.report_inference_success(at(3))
    machine.report_inference_failure(at(4))
    assert machine.state is OperatingState.DEGRADED
    machine.report_outbox_level(BackpressureLevel.CRITICAL, at(5))
    assert machine.state is OperatingState.HALTED


def test_outbox_recovery_closes_gap_and_resumes(store: EdgeStore) -> None:
    machine = make_machine(store)
    machine.report_model_loaded(at(0))
    machine.report_outbox_level(BackpressureLevel.CRITICAL, at(1))
    gap_id = store.open_gaps()[0].gap_id
    # Drained below the warning level (DATABASE.md 11.4 recovery row).
    machine.report_outbox_level(BackpressureLevel.NORMAL, at(2))
    assert machine.state is OperatingState.HEALTHY
    assert machine.halt_reason is None
    assert store.open_gaps() == []
    # The close record is enqueued for delivery, carrying both boundaries.
    close_rows = [
        row
        for row in store.claim_batch(10, now="x")
        if row.idempotency_key == f"{gap_id}:closed"
    ]
    assert len(close_rows) == 1
    assert close_rows[0].payload["ended_at"] is not None
    assert close_rows[0].payload["started_at"] is not None


def test_outbox_warning_alerts_without_transition(
    store: EdgeStore, caplog
) -> None:
    machine = make_machine(store)
    machine.report_model_loaded(at(0))
    with caplog.at_level("WARNING", logger="guardian_lens_edge.state"):
        machine.report_outbox_level(BackpressureLevel.WARNING, at(1))
    assert machine.state is OperatingState.HEALTHY
    assert any("backlog" in record.message for record in caplog.records)


def test_halted_for_model_reasons_does_not_resume_on_outbox_normal(
    store: EdgeStore,
) -> None:
    machine = make_machine(store)
    machine.report_model_load_failed(at(0))
    machine.report_outbox_level(BackpressureLevel.NORMAL, at(1))
    # Operator intervention + restart is the only exit (RS-6).
    assert machine.state is OperatingState.HALTED


def test_restart_after_halt_closes_halt_gaps(store: EdgeStore) -> None:
    crashed = make_machine(store)
    crashed.report_model_load_failed(at(0))
    assert gap_reasons(store) == ["model_load_failed"]
    # Operator fixes the artefact; a fresh process starts over the SAME
    # store (gaps survived the restart) and successfully loads the model.
    restarted = make_machine(store)
    restarted.report_model_loaded(at(60))
    assert restarted.state is OperatingState.HEALTHY
    assert store.open_gaps() == []


def test_inference_reports_ignored_while_halted(store: EdgeStore) -> None:
    machine = make_machine(store)
    machine.report_model_load_failed(at(0))
    for second in range(10):
        machine.report_inference_success(at(second))
    assert machine.state is OperatingState.HALTED


def test_threshold_parameters_are_validated(store: EdgeStore) -> None:
    with pytest.raises(ValueError):
        AgentStateMachine(
            store,
            failure_window=0,
            degraded_failure_rate=0.5,
            halt_failure_rate=0.75,
        )
    with pytest.raises(ValueError):
        AgentStateMachine(
            store,
            failure_window=4,
            degraded_failure_rate=0.8,
            halt_failure_rate=0.5,
        )
