from datetime import datetime, timezone

from guardian_lens_edge.detector import CompositeDetector, Detection
from guardian_lens_edge.frames import Frame


class StubDetector:
    def __init__(self, version: str, class_name: str) -> None:
        self.model_version = version
        self.class_name = class_name

    def detect(self, _frame: Frame) -> list[Detection]:
        return [
            Detection(
                class_name=self.class_name,
                bbox_norm=(0.1, 0.1, 0.2, 0.2),
                confidence=0.8,
            )
        ]


def test_composite_detector_combines_models_with_provenance() -> None:
    detector = CompositeDetector(
        [StubDetector("coco-1", "bottle"), StubDetector("hardhat-1", "hardhat")]
    )
    frame = Frame(
        camera_id="camera-1",
        captured_at=datetime(2026, 8, 20, tzinfo=timezone.utc),
        image_ref="frame.jpg",
        sequence=1,
    )

    detections = detector.detect(frame)

    assert detector.model_version == "coco-1+hardhat-1"
    assert [(item.class_name, item.model_version) for item in detections] == [
        ("bottle", "coco-1"),
        ("hardhat", "hardhat-1"),
    ]
