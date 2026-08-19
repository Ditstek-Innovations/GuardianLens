"""MOD-3 Rule Evaluator — RULE_BOOK.md 5.2 decision table D1, exactly.

Fully deterministic: no inference, no randomness, no wall-clock reads. Time
enters only as ``Frame.captured_at`` (ADR-007). ``point_in_polygon`` and the
threshold comparison are pure functions; the evaluator itself holds only the
dwell/debounce state that D1 rows 4-5 require.

D1, hit policy F (first match wins):

  1. rule inactive            -> no candidate, NOTHING recorded   (BR-001)
  2. confidence < threshold   -> discard + below_threshold count  (BR-D-02)
  3. anchor outside zone      -> discard + outside_zone count     (BR-001)
  4. dwell not yet met        -> hold + dwell_unmet count         (FR-022)
  5. otherwise                -> candidate (status is set by the control
                                 plane, never here — TRD 5.4 layer 1)

plus the debounce band of ARCHITECTURE.md 5.5: a repeat inside the debounce
window is suppressed and counted, never silently dropped.

Failure handling per TRD 4 MOD-3: a missing or malformed rule configuration
means the rule is treated as inactive and an error is logged. Never a
default rule (BR-001).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Protocol, Sequence

from guardian_lens_edge.config import AgentConfig, RuleConfig, ZoneConfig
from guardian_lens_edge.detector import Detection
from guardian_lens_edge.frames import Frame
from guardian_lens_edge.store import CounterKind

__all__ = [
    "CandidateDecision",
    "CounterSink",
    "RuleEvaluator",
    "bbox_anchor",
    "point_in_polygon",
]

logger = logging.getLogger(__name__)

Point = tuple[float, float]


class CounterSink(Protocol):
    """Where discard counters land (EdgeStore in production, BR-D-02)."""

    def increment_counter(
        self,
        bucket_start: str,
        camera_id: str,
        rule_id: str | None,
        counter: CounterKind,
    ) -> None:
        ...


@dataclass(frozen=True)
class CandidateDecision:
    """IF-E3 CandidateEvent input, before the builder adds identity/payload.

    Deliberately carries NO status field: the edge can only ever produce
    unverified candidates, and it is the control plane that stamps
    ``status='unverified'`` on insert (TRD 5.4 — the ingest API rejects any
    payload containing ``status``).
    """

    camera_id: str
    zone: ZoneConfig
    rule: RuleConfig
    confidence: float
    occurred_at: datetime  # frame clock — the edge observation time, ADR-007
    frame: Frame
    # The triggering detection's box (x1,y1,x2,y2 normalised) — carried so
    # the evidence frame can be annotated with WHAT fired and WHERE.
    bbox_norm: tuple[float, float, float, float] | None = None


#: A person detection must itself be reasonably confident before it can
#: serve as context — a 0.05 ghost must not turn a lying phone into a
#: held one. Deterministic constant, documented here, applied everywhere.
_PERSON_CONTEXT_FLOOR = 0.50


def _boxes_overlap(
    a: tuple[float, float, float, float],
    b: tuple[float, float, float, float],
) -> bool:
    """True when two normalised boxes share any area (inclusive edges)."""
    ax1, ay1, ax2, ay2 = a
    bx1, by1, bx2, by2 = b
    return ax1 <= bx2 and ax2 >= bx1 and ay1 <= by2 and ay2 >= by1


def _inside_a_person(candidate, detections) -> bool:
    """True when the candidate is associated with a person in this frame.

    A held phone or bottle often sits on the *edge* of the person box (ear,
    outstretched hand). Requiring the object's centre to fall strictly inside
    the person box dropped those detections, so nothing reached review even
    though the model fired. Overlap of the two boxes is the held-vs-lying
    discriminator: still purely per-frame geometry (BR-D-03), no identity.
    """
    for other in detections:
        if other.class_name != "person":
            continue
        if other.confidence < _PERSON_CONTEXT_FLOOR:
            continue
        if _boxes_overlap(candidate.bbox_norm, other.bbox_norm):
            return True
    return False


def bbox_anchor(bbox_norm: tuple[float, float, float, float]) -> Point:
    """Anchor of a detection for zone membership: bbox bottom-centre.

    Zones are floor areas in normalised image space (DATABASE.md 5.4). For a
    person-scale detection the bottom-centre of the box approximates the
    point of ground contact, which is what "inside the zone" means on a
    floor plan; a box-centre anchor would decide membership at torso height
    and misassign subjects near zone borders. TRD 4 MOD-3 specifies
    "point-in-polygon on detection anchor" without fixing the anchor; this
    is the documented choice.
    """
    x1, y1, x2, y2 = bbox_norm
    return ((x1 + x2) / 2.0, y2)


def _on_segment(px: float, py: float, ax: float, ay: float,
                bx: float, by: float) -> bool:
    """True when (px, py) lies exactly on segment (a, b).

    Exact floating-point arithmetic, deliberately: boundary behaviour must be
    deterministic (TRD 19.2), and an epsilon would turn "on the edge" into a
    tunable. A point whose cross product with the segment is exactly zero and
    which lies within the segment's bounding box is ON the boundary.
    """
    cross = (bx - ax) * (py - ay) - (by - ay) * (px - ax)
    if cross != 0.0:
        return False
    return (
        min(ax, bx) <= px <= max(ax, bx)
        and min(ay, by) <= py <= max(ay, by)
    )


def point_in_polygon(point: Point, polygon: Sequence[Point]) -> bool:
    """Ray-casting point-in-polygon on normalised coordinates.

    Boundary rule, fixed and tested: a point exactly on a vertex or an edge
    is INSIDE. A detection standing on the painted line of a mandatory-PPE
    zone is in the zone — resolving boundary contact toward "outside" would
    silently discard exactly the marginal observations a reviewer should see.

    The even-odd crossing test uses the half-open rule ``(y1 > y) != (y2 > y)``
    so each vertex is counted for exactly one of its two edges; with the
    explicit boundary check above it, every input has one deterministic
    answer.
    """
    if len(polygon) < 3:
        raise ValueError("polygon requires at least 3 vertices")
    px, py = point
    count = len(polygon)
    for i in range(count):
        ax, ay = polygon[i]
        bx, by = polygon[(i + 1) % count]
        if _on_segment(px, py, ax, ay, bx, by):
            return True
    inside = False
    for i in range(count):
        ax, ay = polygon[i]
        bx, by = polygon[(i + 1) % count]
        if (ay > py) != (by > py):
            x_cross = ax + (py - ay) * (bx - ax) / (by - ay)
            if px < x_cross:
                inside = not inside
    return inside


def _hour_bucket(instant: datetime) -> str:
    return (
        instant.astimezone(timezone.utc)
        .replace(minute=0, second=0, microsecond=0)
        .isoformat()
    )


@dataclass
class _DwellState:
    held_since: datetime


class RuleEvaluator:
    """Applies D1 to each frame's detections under the applied configuration.

    Holds per-(camera, zone, rule) dwell and debounce state. All state is
    keyed and advanced exclusively by frame timestamps; two runs over the
    same frames produce identical output.
    """

    def __init__(self, counters: CounterSink) -> None:
        self._counters = counters
        self._config: AgentConfig | None = None
        self._dwell: dict[tuple[str, str, str], _DwellState] = {}
        self._last_emitted: dict[tuple[str, str, str], datetime] = {}
        # Last evaluate() miss reasons — operational diagnostics only.
        self.last_misses: list[str] = []

    def apply_config(self, config: AgentConfig | None) -> None:
        """Swap the active rule set atomically.

        Dwell/debounce state survives a config apply for keys that still
        exist, so a routine config sync does not re-fire continuing
        conditions.
        """
        self._config = config

    def evaluate(
        self, frame: Frame, detections: Sequence[Detection]
    ) -> list[CandidateDecision]:
        """Run D1 for one sampled frame. Returns zero or more candidates."""
        self.last_misses = []
        if self._config is None:
            self.last_misses.append(
                "no agent config applied yet — rules cannot fire"
            )
            return []
        seen = sorted({item.class_name for item in detections})
        seen_text = ", ".join(seen) if seen else "(none)"
        candidates: list[CandidateDecision] = []
        rules_for_camera = 0
        # Deterministic rule order regardless of document order.
        for rule in sorted(self._config.rules, key=lambda r: r.rule_id):
            # D1 row 1 — inactive rule: no candidate, nothing recorded at
            # all. Not even a counter: BR-001 says an inactive rule produces
            # no observable output of any kind.
            if not rule.is_active:
                continue
            zone = self._config.zone_by_id(rule.zone_id)
            if zone is None:
                # TRD 4 MOD-3 failure row: malformed configuration → the
                # rule is treated as inactive and an error is logged.
                logger.error(
                    "rule references unknown zone; treating rule as inactive:"
                    " rule_id=%s zone_id=%s",
                    rule.rule_id,
                    rule.zone_id,
                )
                self.last_misses.append(
                    f"rule {rule.human_readable!r} zone {rule.zone_id} missing"
                )
                continue
            if zone.camera_id != frame.camera_id:
                continue
            rules_for_camera += 1
            candidate, miss = self._evaluate_rule(
                frame, rule, zone, detections, seen_text
            )
            if candidate is not None:
                candidates.append(candidate)
            elif miss is not None:
                self.last_misses.append(miss)
        if rules_for_camera == 0:
            self.last_misses.append(
                f"no active rule on this camera ({frame.camera_id})"
            )
        return candidates

    def _evaluate_rule(
        self,
        frame: Frame,
        rule: RuleConfig,
        zone: ZoneConfig,
        detections: Sequence[Detection],
        seen_text: str,
    ) -> tuple[CandidateDecision | None, str | None]:
        bucket = _hour_bucket(frame.captured_at)
        key = (frame.camera_id, zone.zone_id, rule.rule_id)
        best_confidence: float | None = None
        best_bbox: tuple[float, float, float, float] | None = None
        saw_class = False
        reject: str | None = None
        for detection in detections:
            if detection.class_name != rule.detection_class:
                # Not this rule's condition; another rule may consume it.
                continue
            saw_class = True
            # D1 row 2 — threshold. Comparison is >=: a detection exactly at
            # the configured limit passes (TRD 19.2 boundary target).
            if not detection.confidence >= rule.confidence_threshold:
                self._counters.increment_counter(
                    bucket,
                    frame.camera_id,
                    rule.rule_id,
                    CounterKind.BELOW_THRESHOLD,
                )
                reject = (
                    f"rule {rule.human_readable!r} class "
                    f"{rule.detection_class!r}: confidence "
                    f"{detection.confidence:.2f} < threshold "
                    f"{rule.confidence_threshold:.2f}"
                )
                continue
            # D1 row 3 — zone. Anchor is the bbox bottom-centre.
            if not point_in_polygon(bbox_anchor(detection.bbox_norm),
                                    zone.polygon):
                self._counters.increment_counter(
                    bucket,
                    frame.camera_id,
                    rule.rule_id,
                    CounterKind.OUTSIDE_ZONE,
                )
                reject = (
                    f"rule {rule.human_readable!r} class "
                    f"{rule.detection_class!r}: bbox outside zone {zone.name!r}"
                )
                continue
            # Person-context — the held-vs-lying discriminator. Purely
            # per-frame geometry (BR-D-03: deterministic, no inference
            # after detection): the condition's box must overlap a person
            # box. No identity is read or kept.
            if rule.must_be_carried and not _inside_a_person(
                detection, detections
            ):
                self._counters.increment_counter(
                    bucket,
                    frame.camera_id,
                    rule.rule_id,
                    CounterKind.CONTEXT_UNMET,
                )
                reject = (
                    f"rule {rule.human_readable!r} class "
                    f"{rule.detection_class!r}: must_be_carried but no "
                    f"overlapping person box (person floor "
                    f"{_PERSON_CONTEXT_FLOOR:.2f})"
                )
                continue
            if best_confidence is None or detection.confidence > best_confidence:
                best_confidence = detection.confidence
                best_bbox = detection.bbox_norm

        if best_confidence is None:
            # Condition not observed this sample: a dwell run, if any, is
            # broken — dwell requires the condition to persist across
            # CONSECUTIVE samples.
            self._dwell.pop(key, None)
            if not saw_class:
                return None, (
                    f"rule {rule.human_readable!r} watches "
                    f"{rule.detection_class!r}; frame classes: {seen_text}"
                )
            return None, reject

        # D1 row 4 — dwell. The condition must have persisted for at least
        # dwell_seconds; elapsed exactly equal to the limit passes.
        if rule.dwell_seconds:
            state = self._dwell.get(key)
            if state is None:
                state = _DwellState(held_since=frame.captured_at)
                self._dwell[key] = state
            elapsed = (frame.captured_at - state.held_since).total_seconds()
            if elapsed < rule.dwell_seconds:
                self._counters.increment_counter(
                    bucket, frame.camera_id, rule.rule_id,
                    CounterKind.DWELL_UNMET,
                )
                return None, (
                    f"rule {rule.human_readable!r}: dwell unmet "
                    f"({elapsed:.1f}s < {rule.dwell_seconds}s)"
                )

        # Debounce — suppress a repeat of a continuing condition within
        # debounce_seconds of the LAST EMITTED candidate. A repeat at
        # exactly debounce_seconds is emitted (window is [0, debounce)).
        last_emitted = self._last_emitted.get(key)
        if last_emitted is not None and rule.debounce_seconds > 0:
            since_emit = (frame.captured_at - last_emitted).total_seconds()
            if since_emit < rule.debounce_seconds:
                self._counters.increment_counter(
                    bucket, frame.camera_id, rule.rule_id,
                    CounterKind.DEBOUNCE_SUPPRESSED,
                )
                return None, (
                    f"rule {rule.human_readable!r}: debounce "
                    f"({since_emit:.1f}s < {rule.debounce_seconds}s)"
                )

        # D1 row 5 — candidate. The highest-confidence satisfying detection
        # is the one recorded (deterministic tie-break: first seen wins).
        self._last_emitted[key] = frame.captured_at
        return CandidateDecision(
            camera_id=frame.camera_id,
            zone=zone,
            rule=rule,
            confidence=best_confidence,
            occurred_at=frame.captured_at,
            frame=frame,
            bbox_norm=best_bbox,
        ), None
