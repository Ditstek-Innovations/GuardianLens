"""Seed detection model versions into the current tenant database.

The 2026-08-19 cluster dump (GL-gl_control-202608191022.sql) stored
model_versions on the tenant DBs, not on gl_control. This script copies that
COCO row into the live tenant and adds the hard-hat + synthetic sandbox
versions, with card/datasheet references so gate G1 approval is possible.

Usage (with .env sourced, postgres up):

    .venv/bin/python scripts/seed_detection_models.py
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import psycopg
from psycopg.types.json import Json

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from guardian_lens.db.urls import psycopg_url  # noqa: E402

TENANT = os.environ.get("GL_DEMO_TENANT", "pilot")

# Exact COCO class list from the dump (gl_tenant_pilot / gl_tenant_pilot5).
COCO_CLASSES = [
    "person",
    "bicycle",
    "car",
    "motorcycle",
    "airplane",
    "bus",
    "train",
    "truck",
    "boat",
    "traffic light",
    "fire hydrant",
    "stop sign",
    "parking meter",
    "bench",
    "bird",
    "cat",
    "dog",
    "horse",
    "sheep",
    "cow",
    "elephant",
    "bear",
    "zebra",
    "giraffe",
    "backpack",
    "umbrella",
    "handbag",
    "tie",
    "suitcase",
    "frisbee",
    "skis",
    "snowboard",
    "sports ball",
    "kite",
    "baseball bat",
    "baseball glove",
    "skateboard",
    "surfboard",
    "tennis racket",
    "bottle",
    "wine glass",
    "cup",
    "fork",
    "knife",
    "spoon",
    "bowl",
    "banana",
    "apple",
    "sandwich",
    "orange",
    "broccoli",
    "carrot",
    "hot dog",
    "pizza",
    "donut",
    "cake",
    "chair",
    "couch",
    "potted plant",
    "bed",
    "dining table",
    "toilet",
    "tv",
    "laptop",
    "mouse",
    "remote",
    "keyboard",
    "cell phone",
    "microwave",
    "oven",
    "toaster",
    "sink",
    "refrigerator",
    "book",
    "clock",
    "vase",
    "scissors",
    "teddy bear",
    "hair drier",
    "toothbrush",
]

# Dump row id from gl_tenant_pilot; kept so re-seeds stay stable.
DUMP_COCO_ID = "d3f3cd02-c50c-49a3-a199-9beeffdcf9e1"

MODELS = [
    {
        "id": DUMP_COCO_ID,
        "version": "yolov8n-coco-0.1.0-dev",
        "artefact_hash": "sha256:coco-dev",
        "classes": COCO_CLASSES,
        "model_card_ref": "Docs/models/yolov8n-coco-0.1.0-dev/CARD.md",
        "datasheet_ref": "Docs/models/yolov8n-coco-0.1.0-dev/DATASHEET.md",
        "notes": (
            "DEV EVALUATION ONLY — not G1-approved for site deployment. "
            "Seeded from GL-gl_control-202608191022.sql (tenant model_versions)."
        ),
    },
    {
        "id": "a8c1e4f0-5d2b-4a91-9c3e-7b1f0d6a2e44",
        "version": "hardhat-yolov8n-0.1.0-dev",
        "artefact_hash": "sha256:hardhat-dev",
        "classes": ["hardhat", "person_without_helmet"],
        "model_card_ref": "Docs/models/hardhat-yolov8n-0.1.0-dev/CARD.md",
        "datasheet_ref": "Docs/models/hardhat-yolov8n-0.1.0-dev/DATASHEET.md",
        "notes": "DEV EVALUATION ONLY — not G1-approved for site deployment.",
    },
    {
        "id": "c0ffee00-5e0d-4d00-9e00-000000000001",
        "version": "synthetic-0.0.0",
        "artefact_hash": "sha256:synthetic",
        "classes": ["person_without_helmet", "bottle", "person"],
        "model_card_ref": "Docs/models/yolov8n-coco-0.1.0-dev/CARD.md",
        "datasheet_ref": "Docs/models/yolov8n-coco-0.1.0-dev/DATASHEET.md",
        "notes": "SyntheticDetector sandbox identity used by scripts/edge_demo.py.",
    },
]


def main() -> int:
    url = os.environ.get(
        "GL_TENANT_DB_URL",
        f"postgresql+psycopg://postgres:5003@localhost:5433/gl_tenant_{TENANT}",
    )
    insert = """
        INSERT INTO model_versions (
            id, version, artefact_hash, classes,
            model_card_ref, datasheet_ref, notes
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (version) DO UPDATE SET
            classes = EXCLUDED.classes,
            model_card_ref = COALESCE(model_versions.model_card_ref, EXCLUDED.model_card_ref),
            datasheet_ref = COALESCE(model_versions.datasheet_ref, EXCLUDED.datasheet_ref),
            notes = COALESCE(model_versions.notes, EXCLUDED.notes)
        RETURNING version, (xmax = 0) AS inserted
    """
    with psycopg.connect(psycopg_url(url)) as conn:
        for model in MODELS:
            row = conn.execute(
                insert,
                (
                    model["id"],
                    model["version"],
                    model["artefact_hash"],
                    Json(model["classes"]),
                    model["model_card_ref"],
                    model["datasheet_ref"],
                    model["notes"],
                ),
            ).fetchone()
            assert row is not None
            action = "inserted" if row[1] else "updated"
            print(f"  {action}: {row[0]}")
        conn.commit()
        listed = conn.execute(
            "SELECT version, jsonb_array_length(classes) AS n_classes, "
            "model_card_ref IS NOT NULL AS has_card, approved_at IS NOT NULL AS approved "
            "FROM model_versions ORDER BY version"
        ).fetchall()
    print(f"model_versions in {url.rsplit('/', 1)[-1]}:")
    for version, n_classes, has_card, approved in listed:
        print(f"  {version}  classes={n_classes}  card={has_card}  approved={approved}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
