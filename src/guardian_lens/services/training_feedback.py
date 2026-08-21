"""Build and train a YOLO candidate from human-reviewed event crops.

The live detector is never modified here. A training run writes a separate
candidate artefact and manifest; model registration/approval/deployment stay
explicit governance steps. Accepted/corrected predictions become positive
examples. Only rejections explicitly confirmed as false positives become
negative crops; bulk or ambiguous rejections remain excluded.
"""

from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass
from pathlib import Path
from collections.abc import Callable
from typing import Any

import sqlalchemy as sa
from sqlalchemy.orm import Session

from guardian_lens.repositories.evidence import EvidenceStore
from guardian_lens.repositories.tables import events, training_samples

__all__ = ["DatasetBuild", "FeedbackTrainer", "InsufficientFeedbackError"]

_log = logging.getLogger(__name__)


class InsufficientFeedbackError(RuntimeError):
    pass


@dataclass(frozen=True)
class DatasetBuild:
    root: Path
    dataset_hash: str
    sample_count: int
    classes: tuple[str, ...]


class FeedbackTrainer:
    def __init__(
        self,
        session: Session,
        evidence_store: EvidenceStore,
        output_root: str | Path,
    ) -> None:
        self._session = session
        self._evidence = evidence_store
        self._output_root = Path(output_root)

    def build_dataset(self, *, minimum_samples: int = 20) -> DatasetBuild:
        rows = self._session.execute(
            sa.select(
                training_samples.c.id,
                training_samples.c.event_id,
                training_samples.c.class_name,
                training_samples.c.bbox_norm,
                training_samples.c.decision_type,
                events.c.evidence_ref,
            )
            .select_from(
                training_samples.join(
                    events, training_samples.c.event_id == events.c.id
                )
            )
            .where(
                training_samples.c.eligible.is_(True),
                events.c.evidence_state == "present",
                events.c.evidence_ref.is_not(None),
            )
            .order_by(training_samples.c.reviewed_at, training_samples.c.id)
        ).all()
        if len(rows) < minimum_samples:
            raise InsufficientFeedbackError(
                f"need at least {minimum_samples} eligible reviewed samples; "
                f"found {len(rows)}"
            )

        classes = tuple(sorted({str(row.class_name) for row in rows}))
        class_ids = {name: index for index, name in enumerate(classes)}
        digest = hashlib.sha256()
        for row in rows:
            digest.update(
                json.dumps(
                    [str(row.id), row.class_name, row.bbox_norm],
                    sort_keys=True,
                    separators=(",", ":"),
                ).encode()
            )
        dataset_hash = digest.hexdigest()[:16]
        root = self._output_root / "datasets" / dataset_hash
        for split in ("train", "val"):
            (root / "images" / split).mkdir(parents=True, exist_ok=True)
            (root / "labels" / split).mkdir(parents=True, exist_ok=True)

        exported = 0
        for row in rows:
            content = self._evidence.get(str(row.evidence_ref))
            if content is None:
                _log.warning("training evidence missing for event %s", row.event_id)
                continue
            split = self._split_for(str(row.event_id))
            image, positive_label = self._crop_and_label(
                content,
                tuple(float(value) for value in row.bbox_norm),
                class_ids[str(row.class_name)],
            )
            label = "" if row.decision_type == "reject" else positive_label
            stem = str(row.event_id)
            (root / "images" / split / f"{stem}.jpg").write_bytes(image)
            (root / "labels" / split / f"{stem}.txt").write_text(
                (label + "\n") if label else "", encoding="utf-8"
            )
            exported += 1

        if exported < minimum_samples:
            raise InsufficientFeedbackError(
                f"only {exported} training images were readable; need {minimum_samples}"
            )
        data_yaml = root / "data.yaml"
        names = "\n".join(
            f"  {index}: {json.dumps(name)}"
            for index, name in enumerate(classes)
        )
        data_yaml.write_text(
            f"path: {root.resolve()}\ntrain: images/train\nval: images/val\nnames:\n{names}\n",
            encoding="utf-8",
        )
        manifest = {
            "dataset_hash": dataset_hash,
            "sample_count": exported,
            "classes": list(classes),
            "source": "human-reviewed Guardian Lens event crops",
        }
        (root / "manifest.json").write_text(
            json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        return DatasetBuild(root, dataset_hash, exported, classes)

    def train_candidate(
        self,
        dataset: DatasetBuild,
        *,
        base_model: str | Path,
        epochs: int = 40,
        image_size: int = 640,
        progress_callback: Callable[[int, int], None] | None = None,
    ) -> Path:
        try:
            from ultralytics import YOLO
        except ImportError as exc:  # pragma: no cover - environment dependent
            raise RuntimeError(
                "training dependencies are missing; install with "
                "pip install -e '.[training]'"
            ) from exc

        runs_root = self._output_root / "runs"
        model = YOLO(str(base_model))
        if progress_callback is not None:
            def on_train_epoch_end(trainer: Any) -> None:
                current = int(trainer.epoch) + 1
                total = int(trainer.epochs)
                progress_callback(current, total)

            model.add_callback("on_train_epoch_end", on_train_epoch_end)
        result = model.train(
            data=str(dataset.root / "data.yaml"),
            epochs=epochs,
            imgsz=image_size,
            project=str(runs_root),
            name=dataset.dataset_hash,
            exist_ok=True,
        )
        best = Path(result.save_dir) / "weights" / "best.pt"
        if not best.is_file():
            raise RuntimeError("training completed without a best.pt artefact")
        return best

    @staticmethod
    def _split_for(event_id: str) -> str:
        # Stable 80/20 split: rebuilding the same reviewed set never leaks a
        # frame between train and validation partitions.
        bucket = int(hashlib.sha256(event_id.encode()).hexdigest()[:8], 16)
        return "val" if bucket % 5 == 0 else "train"

    @staticmethod
    def _crop_and_label(
        jpeg: bytes,
        bbox: tuple[float, float, float, float],
        class_id: int,
    ) -> tuple[bytes, str]:
        import cv2
        import numpy as np

        image = cv2.imdecode(np.frombuffer(jpeg, dtype=np.uint8), cv2.IMREAD_COLOR)
        if image is None:
            raise ValueError("training evidence is not a decodable JPEG")
        height, width = image.shape[:2]
        x1, y1, x2, y2 = bbox
        box_width, box_height = x2 - x1, y2 - y1
        # A padded object crop avoids claiming that every unreviewed object
        # elsewhere in the full frame is background.
        pad_x, pad_y = box_width * 0.5, box_height * 0.5
        crop_x1, crop_y1 = max(0.0, x1 - pad_x), max(0.0, y1 - pad_y)
        crop_x2, crop_y2 = min(1.0, x2 + pad_x), min(1.0, y2 + pad_y)
        left, top = int(crop_x1 * width), int(crop_y1 * height)
        right = max(left + 1, int(crop_x2 * width))
        bottom = max(top + 1, int(crop_y2 * height))
        crop = image[top:bottom, left:right]
        ok, encoded = cv2.imencode(".jpg", crop, [cv2.IMWRITE_JPEG_QUALITY, 95])
        if not ok:
            raise ValueError("training crop could not be encoded")

        crop_w, crop_h = crop_x2 - crop_x1, crop_y2 - crop_y1
        label_x1, label_x2 = (x1 - crop_x1) / crop_w, (x2 - crop_x1) / crop_w
        label_y1, label_y2 = (y1 - crop_y1) / crop_h, (y2 - crop_y1) / crop_h
        center_x, center_y = (label_x1 + label_x2) / 2, (label_y1 + label_y2) / 2
        label_w, label_h = label_x2 - label_x1, label_y2 - label_y1
        return encoded.tobytes(), (
            f"{class_id} {center_x:.6f} {center_y:.6f} {label_w:.6f} {label_h:.6f}"
        )
