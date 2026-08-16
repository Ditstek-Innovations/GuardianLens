"""The held-vs-lying discriminator — per-frame person-context geometry.

BR-D-03: pure arithmetic on already-produced detections; a failed check
is counted (context_unmet), never silent (BR-D-02).
"""

from __future__ import annotations

from guardian_lens_edge.detector import Detection
from guardian_lens_edge.store import CounterKind

from tests.edge.test_rules import HELMET_CLASS, detection, make_evaluator
from tests.edge.conftest import make_frame

#: A person box covering the middle of the frame.
PERSON_BBOX = (0.3, 0.2, 0.7, 0.9)


def person(confidence: float = 0.9) -> Detection:
    return Detection(class_name="person", bbox_norm=PERSON_BBOX, confidence=confidence)


def test_condition_inside_a_person_fires():
    evaluator, _ = make_evaluator(must_be_carried=True)
    # Condition bbox centre (0.5, 0.625) lies inside PERSON_BBOX.
    candidates = evaluator.evaluate(make_frame(), [person(), detection()])
    assert len(candidates) == 1
    assert candidates[0].bbox_norm is not None


def test_condition_without_any_person_is_counted_not_fired():
    evaluator, counters = make_evaluator(must_be_carried=True)
    candidates = evaluator.evaluate(make_frame(), [detection()])
    assert candidates == []
    assert counters.kinds().count(CounterKind.CONTEXT_UNMET) == 1


def test_condition_outside_the_person_box_does_not_fire():
    evaluator, counters = make_evaluator(must_be_carried=True)
    # A lying phone: same class, clearly inside the zone but outside the
    # person's box (centre 0.80 vs person x-range 0.3-0.7).
    lying = detection(bbox=(0.72, 0.4, 0.88, 0.85))
    candidates = evaluator.evaluate(make_frame(), [person(), lying])
    assert candidates == []
    assert counters.kinds().count(CounterKind.CONTEXT_UNMET) == 1


def test_low_confidence_person_is_not_context():
    evaluator, counters = make_evaluator(must_be_carried=True)
    ghost = person(confidence=0.2)  # below the 0.50 context floor
    candidates = evaluator.evaluate(make_frame(), [ghost, detection()])
    assert candidates == []
    assert counters.kinds().count(CounterKind.CONTEXT_UNMET) == 1


def test_flag_off_keeps_original_behaviour():
    evaluator, _ = make_evaluator(must_be_carried=False)
    candidates = evaluator.evaluate(make_frame(), [detection()])
    assert len(candidates) == 1
