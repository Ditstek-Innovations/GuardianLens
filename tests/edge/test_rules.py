"""MOD-3 evaluator — D1 exactly, with the TRD 19.2 boundary battery."""

from __future__ import annotations

import pytest

from guardian_lens_edge.detector import Detection
from guardian_lens_edge.rules import (
    RuleEvaluator,
    bbox_anchor,
    point_in_polygon,
)
from guardian_lens_edge.store import CounterKind

from tests.edge.conftest import (
    CAMERA_ID,
    RULE_ID,
    SQUARE,
    RecordingCounters,
    make_config,
    make_frame,
)

HELMET_CLASS = "person_without_helmet"

# Anchored inside SQUARE: bottom-centre (0.5, 0.85).
INSIDE_BBOX = (0.4, 0.4, 0.6, 0.85)


def detection(
    confidence: float = 0.9,
    bbox: tuple[float, float, float, float] = INSIDE_BBOX,
    class_name: str = HELMET_CLASS,
) -> Detection:
    return Detection(class_name=class_name, bbox_norm=bbox, confidence=confidence)


def make_evaluator(**config_kwargs) -> tuple[RuleEvaluator, RecordingCounters]:
    counters = RecordingCounters()
    evaluator = RuleEvaluator(counters)
    evaluator.apply_config(make_config(**config_kwargs))
    return evaluator, counters


# ----------------------------------------------------------------------
# point_in_polygon geometry — boundary cases are deterministic and INSIDE
# ----------------------------------------------------------------------


def test_point_strictly_inside() -> None:
    assert point_in_polygon((0.5, 0.5), SQUARE) is True


def test_point_strictly_outside() -> None:
    assert point_in_polygon((0.95, 0.5), SQUARE) is False


def test_point_exactly_on_vertex_is_inside() -> None:
    for vertex in SQUARE:
        assert point_in_polygon(vertex, SQUARE) is True


def test_point_exactly_on_edge_is_inside() -> None:
    assert point_in_polygon((0.5, 0.1), SQUARE) is True   # top edge
    assert point_in_polygon((0.9, 0.5), SQUARE) is True   # right edge
    assert point_in_polygon((0.5, 0.9), SQUARE) is True   # bottom edge
    assert point_in_polygon((0.1, 0.5), SQUARE) is True   # left edge


def test_point_collinear_with_edge_but_beyond_it_is_outside() -> None:
    # Same y as the top edge, x beyond the segment: collinear, not on it.
    assert point_in_polygon((0.95, 0.1), SQUARE) is False
    assert point_in_polygon((0.05, 0.1), SQUARE) is False


def test_non_convex_polygon() -> None:
    # An L-shape: (0.5, 0.75) sits in the notch, outside the polygon.
    l_shape = [(0.0, 0.0), (1.0, 0.0), (1.0, 0.5),
               (0.5, 0.5), (0.5, 1.0), (0.0, 1.0)]
    assert point_in_polygon((0.25, 0.75), l_shape) is True
    assert point_in_polygon((0.75, 0.75), l_shape) is False


def test_degenerate_polygon_rejected() -> None:
    with pytest.raises(ValueError):
        point_in_polygon((0.5, 0.5), [(0.0, 0.0), (1.0, 1.0)])


def test_anchor_is_bbox_bottom_centre() -> None:
    assert bbox_anchor((0.2, 0.1, 0.6, 0.8)) == (0.4, 0.8)


# ----------------------------------------------------------------------
# D1 row 1 — inactive rule: nothing recorded at all (BR-001)
# ----------------------------------------------------------------------


def test_inactive_rule_records_nothing_at_all() -> None:
    evaluator, counters = make_evaluator(is_active=False)
    candidates = evaluator.evaluate(make_frame(), [detection(confidence=0.99)])
    assert candidates == []
    assert counters.calls == []


def test_no_configuration_means_no_candidates_and_no_counters() -> None:
    counters = RecordingCounters()
    evaluator = RuleEvaluator(counters)  # no apply_config: nothing exists
    assert evaluator.evaluate(make_frame(), [detection()]) == []
    assert counters.calls == []


# ----------------------------------------------------------------------
# D1 row 2 — threshold; >= at the limit passes (TRD 19.2)
# ----------------------------------------------------------------------


def test_confidence_exactly_at_threshold_passes() -> None:
    evaluator, counters = make_evaluator(confidence_threshold=0.5)
    candidates = evaluator.evaluate(make_frame(), [detection(confidence=0.5)])
    assert len(candidates) == 1
    assert candidates[0].confidence == 0.5
    assert counters.calls == []


def test_candidate_retains_triggering_model_version() -> None:
    evaluator, _ = make_evaluator(confidence_threshold=0.5)
    candidates = evaluator.evaluate(
        make_frame(),
        [
            Detection(
                class_name=HELMET_CLASS,
                bbox_norm=INSIDE_BBOX,
                confidence=0.9,
                model_version="hardhat-1",
            )
        ],
    )

    assert candidates[0].model_version == "hardhat-1"


def test_confidence_just_below_threshold_discards_and_counts() -> None:
    evaluator, counters = make_evaluator(confidence_threshold=0.5)
    candidates = evaluator.evaluate(
        make_frame(), [detection(confidence=0.4999999)]
    )
    assert candidates == []
    assert counters.kinds() == [CounterKind.BELOW_THRESHOLD]
    bucket, camera_id, rule_id, _ = counters.calls[0]
    assert camera_id == CAMERA_ID
    assert rule_id == RULE_ID
    assert bucket == "2026-08-12T09:00:00+00:00"


# ----------------------------------------------------------------------
# D1 row 3 — zone; anchor decides, and it is the bottom-centre
# ----------------------------------------------------------------------


def test_bbox_centre_inside_but_anchor_outside_discards_and_counts() -> None:
    evaluator, counters = make_evaluator()
    # Centre (0.5, 0.725) is inside the square, bottom-centre (0.5, 0.95)
    # is below it: with a bottom-centre anchor this must be OUTSIDE.
    straddling = detection(bbox=(0.4, 0.5, 0.6, 0.95))
    candidates = evaluator.evaluate(make_frame(), [straddling])
    assert candidates == []
    assert counters.kinds() == [CounterKind.OUTSIDE_ZONE]


def test_anchor_on_zone_vertex_is_admitted() -> None:
    evaluator, counters = make_evaluator()
    on_vertex = detection(bbox=(0.05, 0.0, 0.15, 0.1))  # anchor (0.1, 0.1)
    assert len(evaluator.evaluate(make_frame(), [on_vertex])) == 1
    assert counters.calls == []


def test_anchor_on_zone_edge_is_admitted() -> None:
    evaluator, counters = make_evaluator()
    on_edge = detection(bbox=(0.4, 0.0, 0.6, 0.1))  # anchor (0.5, 0.1)
    assert len(evaluator.evaluate(make_frame(), [on_edge])) == 1
    assert counters.calls == []


# ----------------------------------------------------------------------
# D1 row 4 — dwell; exactly dwell_seconds passes; interruption resets
# ----------------------------------------------------------------------


def test_dwell_unmet_holds_and_counts() -> None:
    evaluator, counters = make_evaluator(dwell_seconds=4)
    assert evaluator.evaluate(make_frame(0.0, 0), [detection()]) == []
    assert evaluator.evaluate(make_frame(2.0, 1), [detection()]) == []
    assert counters.kinds() == [
        CounterKind.DWELL_UNMET,
        CounterKind.DWELL_UNMET,
    ]


def test_dwell_exactly_at_limit_passes() -> None:
    evaluator, _ = make_evaluator(dwell_seconds=4)
    assert evaluator.evaluate(make_frame(0.0, 0), [detection()]) == []
    assert evaluator.evaluate(make_frame(2.0, 1), [detection()]) == []
    emitted = evaluator.evaluate(make_frame(4.0, 2), [detection()])
    assert len(emitted) == 1
    assert emitted[0].occurred_at == make_frame(4.0).captured_at


def test_dwell_interruption_resets_the_run() -> None:
    evaluator, counters = make_evaluator(dwell_seconds=4)
    assert evaluator.evaluate(make_frame(0.0, 0), [detection()]) == []
    # Condition absent for one sample: the run is broken.
    assert evaluator.evaluate(make_frame(2.0, 1), []) == []
    # 4s after the ORIGINAL start, but only 0s into the new run: still held.
    assert evaluator.evaluate(make_frame(4.0, 2), [detection()]) == []
    assert evaluator.evaluate(make_frame(6.0, 3), [detection()]) == []
    emitted = evaluator.evaluate(make_frame(8.0, 4), [detection()])
    assert len(emitted) == 1
    assert counters.kinds().count(CounterKind.DWELL_UNMET) == 3


def test_no_dwell_configured_fires_on_first_sample() -> None:
    evaluator, counters = make_evaluator(dwell_seconds=None)
    assert len(evaluator.evaluate(make_frame(), [detection()])) == 1
    assert counters.calls == []


# ----------------------------------------------------------------------
# Debounce — suppressed repeats are counted; exactly at the window emits
# ----------------------------------------------------------------------


def test_repeat_within_debounce_window_is_suppressed_and_counted() -> None:
    evaluator, counters = make_evaluator(debounce_seconds=30)
    assert len(evaluator.evaluate(make_frame(0.0, 0), [detection()])) == 1
    assert evaluator.evaluate(make_frame(10.0, 1), [detection()]) == []
    assert evaluator.evaluate(make_frame(29.0, 2), [detection()]) == []
    assert counters.kinds() == [
        CounterKind.DEBOUNCE_SUPPRESSED,
        CounterKind.DEBOUNCE_SUPPRESSED,
    ]


def test_repeat_at_exactly_debounce_seconds_is_emitted() -> None:
    evaluator, counters = make_evaluator(debounce_seconds=30)
    assert len(evaluator.evaluate(make_frame(0.0, 0), [detection()])) == 1
    emitted = evaluator.evaluate(make_frame(30.0, 1), [detection()])
    assert len(emitted) == 1
    assert counters.calls == []


def test_debounce_window_restarts_from_each_emission() -> None:
    evaluator, counters = make_evaluator(debounce_seconds=30)
    assert len(evaluator.evaluate(make_frame(0.0, 0), [detection()])) == 1
    assert len(evaluator.evaluate(make_frame(30.0, 1), [detection()])) == 1
    # 50s is 20s after the SECOND emission: suppressed.
    assert evaluator.evaluate(make_frame(50.0, 2), [detection()]) == []
    assert counters.kinds() == [CounterKind.DEBOUNCE_SUPPRESSED]


# ----------------------------------------------------------------------
# Candidate content and misc determinism
# ----------------------------------------------------------------------


def test_candidate_carries_frame_time_and_best_confidence() -> None:
    evaluator, _ = make_evaluator()
    frame = make_frame(7.0)
    emitted = evaluator.evaluate(
        frame, [detection(confidence=0.6), detection(confidence=0.8)]
    )
    assert len(emitted) == 1
    assert emitted[0].confidence == 0.8
    assert emitted[0].occurred_at == frame.captured_at
    assert emitted[0].camera_id == CAMERA_ID


def test_candidate_has_no_status_attribute() -> None:
    # TRD 5.4 layer 1: the edge cannot express a status at all.
    evaluator, _ = make_evaluator()
    emitted = evaluator.evaluate(make_frame(), [detection()])
    assert not hasattr(emitted[0], "status")


def test_other_detection_classes_are_ignored_entirely() -> None:
    evaluator, counters = make_evaluator()
    candidates = evaluator.evaluate(
        make_frame(), [detection(class_name="forklift", confidence=0.99)]
    )
    assert candidates == []
    assert counters.calls == []


def test_frame_for_other_camera_does_not_touch_the_rule() -> None:
    evaluator, counters = make_evaluator()
    other = make_frame(camera_id="99999999-9999-9999-9999-999999999999")
    assert evaluator.evaluate(other, [detection()]) == []
    assert counters.calls == []


def test_must_be_carried_accepts_object_overlapping_person_box() -> None:
    """A phone at the ear often sits on the person-box edge; centre-inside
    would drop it and the review queue would stay empty."""
    evaluator, counters = make_evaluator(
        must_be_carried=True, debounce_seconds=0
    )
    person = detection(
        class_name="person", bbox=(0.30, 0.20, 0.70, 0.90), confidence=0.9
    )
    phone_at_ear = detection(
        class_name=HELMET_CLASS, bbox=(0.68, 0.15, 0.80, 0.28), confidence=0.8
    )
    emitted = evaluator.evaluate(make_frame(), [person, phone_at_ear])
    assert len(emitted) == 1
    assert counters.calls == []


def test_must_be_carried_rejects_object_with_no_person_overlap() -> None:
    evaluator, counters = make_evaluator(
        must_be_carried=True, debounce_seconds=0
    )
    person = detection(
        class_name="person", bbox=(0.10, 0.10, 0.30, 0.50), confidence=0.9
    )
    object_elsewhere = detection(
        class_name=HELMET_CLASS, bbox=(0.60, 0.60, 0.80, 0.85), confidence=0.8
    )
    emitted = evaluator.evaluate(make_frame(), [person, object_elsewhere])
    assert emitted == []
    assert counters.kinds() == [CounterKind.CONTEXT_UNMET]
    assert any("must_be_carried" in miss for miss in evaluator.last_misses)


def test_miss_reason_names_class_mismatch() -> None:
    evaluator, _ = make_evaluator(debounce_seconds=0)
    emitted = evaluator.evaluate(
        make_frame(), [detection(class_name="cell phone", confidence=0.9)]
    )
    assert emitted == []
    assert evaluator.last_misses
    assert "person_without_helmet" in evaluator.last_misses[0]
    assert "cell phone" in evaluator.last_misses[0]


def test_every_discard_path_has_a_distinct_counter() -> None:
    evaluator, counters = make_evaluator(
        confidence_threshold=0.5, debounce_seconds=30, dwell_seconds=2
    )
    frame0 = make_frame(0.0, 0)
    # below threshold
    evaluator.evaluate(frame0, [detection(confidence=0.1)])
    # outside zone (passes threshold)
    evaluator.evaluate(frame0, [detection(bbox=(0.4, 0.5, 0.6, 0.95))])
    # dwell start (held, unmet)
    evaluator.evaluate(make_frame(1.0, 1), [detection()])
    # dwell met at exactly 2s -> emitted
    assert len(evaluator.evaluate(make_frame(3.0, 2), [detection()])) == 1
    # repeat within debounce -> suppressed
    evaluator.evaluate(make_frame(4.0, 3), [detection()])
    assert counters.kinds() == [
        CounterKind.BELOW_THRESHOLD,
        CounterKind.OUTSIDE_ZONE,
        CounterKind.DWELL_UNMET,
        CounterKind.DEBOUNCE_SUPPRESSED,
    ]
