"""Structured predictions and review-derived training feedback.

Revision ID: 0020
Revises: 0019

New events retain a clean JPEG and carry the model's class and normalized
bounding box separately. A review decision creates one immutable feedback
row in the same transaction. Only accepted/corrected samples with complete
annotations are eligible for dataset export. A reviewer may explicitly mark
a rejection as a false-positive crop; bulk/ambiguous rejections stay excluded.
"""

from __future__ import annotations

from alembic import op

revision: str = "0020"
down_revision: str | None = "0019"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE events
            ADD COLUMN predicted_class VARCHAR(100),
            ADD COLUMN predicted_bbox JSONB;

        CREATE TABLE training_samples (
            id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            event_id      UUID NOT NULL UNIQUE
                          REFERENCES events(id) ON DELETE CASCADE,
            site_id       UUID NOT NULL
                          REFERENCES sites(id) ON DELETE RESTRICT,
            decision_type VARCHAR(20) NOT NULL,
            class_name    VARCHAR(100),
            bbox_norm     JSONB,
            eligible      BOOLEAN NOT NULL DEFAULT FALSE,
            reviewed_by   UUID NOT NULL
                          REFERENCES users(id) ON DELETE RESTRICT,
            reviewed_at   TIMESTAMPTZ NOT NULL,
            created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),

            CONSTRAINT chk_training_decision CHECK (
                decision_type IN ('accept', 'reject', 'correct')
            ),
            CONSTRAINT chk_training_eligible_complete CHECK (
                NOT eligible OR (class_name IS NOT NULL AND bbox_norm IS NOT NULL)
            )
        );

        CREATE INDEX idx_training_samples_ready
            ON training_samples (site_id, reviewed_at, id)
            WHERE eligible;
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS training_samples")
    op.execute(
        "ALTER TABLE events DROP COLUMN IF EXISTS predicted_bbox, "
        "DROP COLUMN IF EXISTS predicted_class"
    )
