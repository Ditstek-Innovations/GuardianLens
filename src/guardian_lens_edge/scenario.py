"""Scenario file — the synthetic input that drives the dev-form agent.

Schema (JSON, defined here — no other document specifies it):

A scenario file is a JSON **list** of entries, in ascending ``at_seconds``
order::

    [
      {
        "at_seconds": 0.0,
        "camera_id": "3f6c2f6e-...",
        "detections": [
          {
            "class": "person_without_helmet",
            "bbox": [0.40, 0.35, 0.55, 0.90],
            "confidence": 0.83
          }
        ]
      }
    ]

- ``at_seconds`` — offset from the run's start instant; becomes the frame's
  ``captured_at`` (and therefore the event's ``occurred_at``, ADR-007).
- ``camera_id`` — must match a camera in the agent configuration.
- ``bbox`` — ``[x1, y1, x2, y2]`` in normalised 0-1 image space, matching the
  zone polygon space (DATABASE.md 5.4).
- ``confidence`` — model confidence, 0-1.
- ``detections`` may be empty: an empty list is a frame in which the detector
  saw nothing, which is how dwell interruption is scripted.

One scenario drives both ``SyntheticSource`` (frames) and
``SyntheticDetector`` (detections per frame), keyed by entry index.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

__all__ = ["Scenario", "ScenarioEntry", "ScenarioDetection"]


@dataclass(frozen=True)
class ScenarioDetection:
    class_name: str
    bbox: tuple[float, float, float, float]
    confidence: float


@dataclass(frozen=True)
class ScenarioEntry:
    at_seconds: float
    camera_id: str
    detections: list[ScenarioDetection] = field(default_factory=list)


@dataclass(frozen=True)
class Scenario:
    entries: list[ScenarioEntry]

    @classmethod
    def load(cls, path: str | Path) -> "Scenario":
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
        return cls.from_list(raw)

    @classmethod
    def from_list(cls, raw: object) -> "Scenario":
        if not isinstance(raw, list):
            raise ValueError("scenario file must be a JSON list of entries")
        entries: list[ScenarioEntry] = []
        for index, item in enumerate(raw):
            if not isinstance(item, dict):
                raise ValueError(f"scenario entry {index} is not an object")
            try:
                detections = [
                    ScenarioDetection(
                        class_name=str(detection["class"]),
                        bbox=tuple(float(v) for v in detection["bbox"]),
                        confidence=float(detection["confidence"]),
                    )
                    for detection in item.get("detections", [])
                ]
                entry = ScenarioEntry(
                    at_seconds=float(item["at_seconds"]),
                    camera_id=str(item["camera_id"]),
                    detections=detections,
                )
            except (KeyError, TypeError, ValueError) as exc:
                raise ValueError(
                    f"scenario entry {index} is malformed: {exc}"
                ) from exc
            for detection in entry.detections:
                if len(detection.bbox) != 4:
                    raise ValueError(
                        f"scenario entry {index}: bbox must be [x1,y1,x2,y2]"
                    )
            entries.append(entry)
        return cls(entries=entries)
