"""Frame sources — MOD-1 Stream Manager, development form (TRD 13.2).

Emits ``Frame(camera_id, captured_at, image_ref, sequence)`` (IF-E1,
ARCHITECTURE.md 5.4). In this development form a scenario file or a recorded
video replaces a live camera: the MVP tests the workflow, not the detector,
and a fixed input makes results reproducible.

``captured_at`` is the edge clock at observation time and becomes the
event's ``occurred_at`` (ADR-007). It is stamped here, at the source — no
module downstream reads a wall clock.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Iterator, Protocol

from guardian_lens_edge.scenario import Scenario

__all__ = ["Frame", "FrameSource", "SyntheticSource", "VideoFileSource"]


@dataclass(frozen=True)
class Frame:
    camera_id: str
    captured_at: datetime  # timezone-aware UTC, edge clock (ADR-007)
    image_ref: str  # local file path, or a synthetic/rtsp reference
    sequence: int
    # JPEG bytes of the sampled frame, held in memory only. Live sources
    # (RTSP) carry the frame here so that ONLY frames attached to a
    # candidate event ever reach disk (DATABASE.md 11.5) — the builder
    # spools these bytes when, and only when, a candidate is admitted.
    # ``repr=False``: frame bytes never land in logs or assertion output.
    image_bytes: bytes | None = field(default=None, repr=False)


class FrameSource(Protocol):
    def frames(self) -> Iterator[Frame]:
        """Yield sampled frames in capture order."""
        ...


class SyntheticSource:
    """Frames driven by a scenario file (see ``guardian_lens_edge.scenario``).

    Yields one frame per scenario entry, with ``captured_at`` derived from
    the entry's ``at_seconds`` offset against an injected start instant —
    fully deterministic, no wall-clock reads.

    ``sequence`` is the scenario entry index; ``SyntheticDetector`` uses the
    same index to return that entry's detections, so source and detector must
    share one ``Scenario``.
    """

    def __init__(self, scenario: Scenario, *, start_at: datetime) -> None:
        if start_at.tzinfo is None:
            raise ValueError("start_at must be timezone-aware")
        self._scenario = scenario
        self._start_at = start_at

    def frames(self) -> Iterator[Frame]:
        for index, entry in enumerate(self._scenario.entries):
            yield Frame(
                camera_id=entry.camera_id,
                captured_at=self._start_at
                + timedelta(seconds=entry.at_seconds),
                image_ref=f"synthetic:{entry.camera_id}:{index}",
                sequence=index,
            )


class VideoFileSource:
    """Frames sampled from a recorded video file (TRD 13.2 dev environment).

    OpenCV is imported lazily and is deliberately NOT a declared dependency:
    the workflow tests run with zero ML/vision dependencies, and cv2 is only
    needed when a recorded video actually replaces the scenario file.
    """

    def __init__(
        self,
        video_path: str | Path,
        camera_id: str,
        *,
        sample_rate_fps: float,
        start_at: datetime,
        spool_dir: str | Path,
    ) -> None:
        if sample_rate_fps <= 0:
            raise ValueError("sample_rate_fps must be positive")
        if start_at.tzinfo is None:
            raise ValueError("start_at must be timezone-aware")
        self._video_path = Path(video_path)
        self._camera_id = camera_id
        self._sample_rate_fps = sample_rate_fps
        self._start_at = start_at
        self._spool_dir = Path(spool_dir)

    def frames(self) -> Iterator[Frame]:
        try:
            import cv2  # noqa: PLC0415 — lazy on purpose, see class docstring
        except ImportError as exc:
            raise RuntimeError(
                "VideoFileSource requires opencv-python (cv2), which is not "
                "installed. It is intentionally not a project dependency; "
                "install it explicitly, or use SyntheticSource for "
                "workflow testing (TRD 13.2)."
            ) from exc

        capture = cv2.VideoCapture(str(self._video_path))
        if not capture.isOpened():
            raise RuntimeError(f"cannot open video file: {self._video_path}")
        try:
            native_fps = capture.get(cv2.CAP_PROP_FPS) or self._sample_rate_fps
            step = max(1, round(native_fps / self._sample_rate_fps))
            self._spool_dir.mkdir(parents=True, exist_ok=True)
            frame_index = 0
            sequence = 0
            while True:
                is_read, image = capture.read()
                if not is_read:
                    return
                if frame_index % step == 0:
                    offset_seconds = frame_index / native_fps
                    image_path = (
                        self._spool_dir
                        / f"{self._camera_id}-{sequence}.jpg"
                    )
                    cv2.imwrite(str(image_path), image)
                    yield Frame(
                        camera_id=self._camera_id,
                        captured_at=self._start_at
                        + timedelta(seconds=offset_seconds),
                        image_ref=str(image_path),
                        sequence=sequence,
                    )
                    sequence += 1
                frame_index += 1
        finally:
            capture.release()
