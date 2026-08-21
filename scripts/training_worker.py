#!/usr/bin/env python3
"""Continuously train candidate weights without touching the live model."""

from __future__ import annotations

import json
import logging
import os
import signal
import time
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from guardian_lens.core.settings import load_settings
from guardian_lens.repositories.evidence import FilesystemEvidenceStore
from guardian_lens.services.training_feedback import (
    FeedbackTrainer,
    InsufficientFeedbackError,
)

_stop = False
_status_path = Path("var/training/status.json")


def _write_status(payload: dict) -> None:
    payload = {**payload, "updated_at": datetime.now(UTC).isoformat()}
    _status_path.parent.mkdir(parents=True, exist_ok=True)
    temporary = _status_path.with_suffix(".tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    temporary.replace(_status_path)


def _request_stop(*_: object) -> None:
    global _stop
    _stop = True


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    signal.signal(signal.SIGINT, _request_stop)
    signal.signal(signal.SIGTERM, _request_stop)
    settings = load_settings()
    minimum = int(os.getenv("GL_TRAINING_MINIMUM_SAMPLES", "20"))
    epochs = int(os.getenv("GL_TRAINING_EPOCHS", "40"))
    interval = int(os.getenv("GL_TRAINING_POLL_SECONDS", "60"))
    base_model = os.getenv("GL_TRAINING_BASE_MODEL", "var/models/yolov8n-coco.pt")
    engine = create_engine(settings.tenant_db_url)
    evidence = FilesystemEvidenceStore(settings.evidence_root)
    last_trained_hash: str | None = None
    if _status_path.is_file():
        try:
            previous = json.loads(_status_path.read_text())
            if previous.get("state") == "candidate_ready":
                last_trained_hash = previous.get("dataset_hash")
        except (OSError, ValueError):
            pass

    try:
        while not _stop:
            try:
                with Session(engine) as session:
                    trainer = FeedbackTrainer(session, evidence, "var/training")
                    dataset = trainer.build_dataset(minimum_samples=minimum)
                    if dataset.dataset_hash != last_trained_hash:
                        _write_status(
                            {
                                "state": "training",
                                "dataset_hash": dataset.dataset_hash,
                                "sample_count": dataset.sample_count,
                                "classes": dataset.classes,
                                "minimum_samples": minimum,
                                "current_epoch": 0,
                                "total_epochs": epochs,
                                "progress_percent": 0,
                            }
                        )

                        def report_progress(current: int, total: int) -> None:
                            _write_status(
                                {
                                    "state": "training",
                                    "dataset_hash": dataset.dataset_hash,
                                    "sample_count": dataset.sample_count,
                                    "classes": dataset.classes,
                                    "minimum_samples": minimum,
                                    "current_epoch": current,
                                    "total_epochs": total,
                                    "progress_percent": round(current / total * 100, 1),
                                }
                            )

                        candidate = trainer.train_candidate(
                            dataset,
                            base_model=base_model,
                            epochs=epochs,
                            progress_callback=report_progress,
                        )
                        last_trained_hash = dataset.dataset_hash
                        _write_status(
                            {
                                "state": "candidate_ready",
                                "dataset_hash": dataset.dataset_hash,
                                "sample_count": dataset.sample_count,
                                "classes": dataset.classes,
                                "candidate_path": str(candidate),
                                "deployed": False,
                                "minimum_samples": minimum,
                                "current_epoch": epochs,
                                "total_epochs": epochs,
                                "progress_percent": 100,
                            }
                        )
            except InsufficientFeedbackError as exc:
                _write_status(
                    {
                        "state": "collecting",
                        "detail": str(exc),
                        "minimum_samples": minimum,
                    }
                )
            except Exception as exc:
                logging.exception("feedback training cycle failed")
                _write_status(
                    {"state": "failed", "detail": f"{type(exc).__name__}: {exc}"}
                )

            for _ in range(interval):
                if _stop:
                    break
                time.sleep(1)
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
