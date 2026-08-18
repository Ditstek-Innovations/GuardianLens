"""Model versions, with gate G1 as a constraint.

Revision ID: 0004
Revises: 0003

Rules affected: BR-D-01 (PROPOSED), BR-M-01 (PROPOSED, no technical
enforcement point possible), gate G1.

GOVERNANCE.md 9 requires a complete model card, a dataset datasheet,
held-out evaluation and condition-stratified evaluation before any model
version reaches any site, with a named approver and a named veto holder.
In TRD 9.10 none of that has a home in the schema, so the gate is enforced
entirely by process — and process is what erodes under delivery pressure.

The constraint cannot verify that a model card is GOOD. Nothing in a
database can. It makes deploying a model version with no recorded approver
at all impossible, which is a different and achievable claim — AMD-DB-08.

model_versions rows are never deleted while any event references them
(ON DELETE RESTRICT from events, 0005). That link is evidence: if a version
is later found defective, the affected events must be identifiable exactly,
and deriving the version from a deployment timeline is an approximation.
An approximation is not evidence.
"""

from __future__ import annotations

from alembic import op

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE model_versions (
            id                 UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
            version            VARCHAR(40) NOT NULL,
            -- SHA-256 of the ONNX artefact, verified on load. The agent
            -- refuses to start on mismatch (TRD 12.6 A08).
            artefact_hash      TEXT        NOT NULL,
            training_data_hash TEXT,
            classes            JSONB       NOT NULL,
            model_card_ref     TEXT,
            datasheet_ref      TEXT,
            approved_by        UUID        REFERENCES users(id) ON DELETE RESTRICT,
            approved_at        TIMESTAMPTZ,
            deployed_at        TIMESTAMPTZ,
            -- Known weak conditions, documented rather than averaged into a
            -- single headline figure (TRD 5.8).
            notes              TEXT,

            CONSTRAINT uq_model_versions_version UNIQUE (version),
            CONSTRAINT chk_model_deployed_requires_approval CHECK (
                deployed_at IS NULL
                OR (approved_by IS NOT NULL AND model_card_ref IS NOT NULL)
            )
        )
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS model_versions")
