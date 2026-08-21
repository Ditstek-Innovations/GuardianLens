from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

import cv2
import numpy as np
import pytest
from pydantic import ValidationError

from guardian_lens.schemas.events import DetectionPrediction
from guardian_lens.services.training_feedback import DatasetBuild, FeedbackTrainer


def test_training_crop_produces_valid_yolo_label() -> None:
    image = np.full((200, 300, 3), 127, dtype=np.uint8)
    ok, jpeg = cv2.imencode(".jpg", image)
    assert ok

    cropped, label = FeedbackTrainer._crop_and_label(
        jpeg.tobytes(), (0.25, 0.25, 0.75, 0.75), class_id=2
    )
    decoded = cv2.imdecode(np.frombuffer(cropped, dtype=np.uint8), cv2.IMREAD_COLOR)

    assert decoded is not None
    assert label == "2 0.500000 0.500000 0.500000 0.500000"


@pytest.mark.parametrize(
    "bbox",
    [(-0.1, 0.2, 0.5, 0.8), (0.6, 0.2, 0.5, 0.8), (0.2, 0.8, 0.5, 0.8)],
)
def test_prediction_rejects_invalid_training_boxes(
    bbox: tuple[float, float, float, float],
) -> None:
    with pytest.raises(ValidationError):
        DetectionPrediction(class_name="bottle", bbox_norm=bbox)


def test_candidate_training_reports_each_epoch(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    class FakeYolo:
        def __init__(self, _: str) -> None:
            self.callback = None

        def add_callback(self, _: str, callback: object) -> None:
            self.callback = callback

        def train(self, **_: object) -> SimpleNamespace:
            assert self.callback is not None
            trainer = SimpleNamespace(epoch=0, epochs=2)
            self.callback(trainer)
            trainer.epoch = 1
            self.callback(trainer)
            save_dir = tmp_path / "run"
            (save_dir / "weights").mkdir(parents=True)
            (save_dir / "weights" / "best.pt").write_bytes(b"candidate")
            return SimpleNamespace(save_dir=save_dir)

    monkeypatch.setitem(sys.modules, "ultralytics", SimpleNamespace(YOLO=FakeYolo))
    dataset_root = tmp_path / "dataset"
    dataset_root.mkdir()
    (dataset_root / "data.yaml").write_text("names: {}\n", encoding="utf-8")
    dataset = DatasetBuild(dataset_root, "abc123", 20, ("bottle",))
    trainer = FeedbackTrainer(None, None, tmp_path)  # type: ignore[arg-type]
    progress: list[tuple[int, int]] = []

    candidate = trainer.train_candidate(
        dataset,
        base_model="base.pt",
        epochs=2,
        progress_callback=lambda current, total: progress.append((current, total)),
    )

    assert candidate == tmp_path / "run" / "weights" / "best.pt"
    assert progress == [(1, 2), (2, 2)]
