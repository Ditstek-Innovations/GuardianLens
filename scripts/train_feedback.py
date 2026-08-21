#!/usr/bin/env python3
"""Build reviewed YOLO data and train a separate candidate model."""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from guardian_lens.core.settings import load_settings
from guardian_lens.repositories.evidence import FilesystemEvidenceStore
from guardian_lens.services.training_feedback import FeedbackTrainer


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--minimum-samples", type=int, default=20)
    parser.add_argument("--epochs", type=int, default=40)
    parser.add_argument("--base-model", default="var/models/yolov8n-coco.pt")
    parser.add_argument("--dataset-only", action="store_true")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO)

    settings = load_settings()
    engine = create_engine(settings.tenant_db_url)
    try:
        with Session(engine) as session:
            trainer = FeedbackTrainer(
                session,
                FilesystemEvidenceStore(settings.evidence_root),
                Path("var/training"),
            )
            dataset = trainer.build_dataset(minimum_samples=args.minimum_samples)
            print(
                f"dataset {dataset.dataset_hash}: {dataset.sample_count} samples, "
                f"classes={', '.join(dataset.classes)}"
            )
            if not args.dataset_only:
                candidate = trainer.train_candidate(
                    dataset, base_model=args.base_model, epochs=args.epochs
                )
                print(f"candidate model ready (not deployed): {candidate}")
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
