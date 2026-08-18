"""The events table, with every verification constraint.

Revision ID: 0005
Revises: 0004

*** TIER T3 — GOVERNANCE.md 8.2. ***
Rules affected: BR-004 (ABSOLUTE), BR-005 (ABSOLUTE), BR-007 (STRONG),
BR-D-01 (PROPOSED), FR-043.

This revision creates the fourth and least removable layer of the
defence-in-depth pattern in ARCHITECTURE.md 4.2. The first three layers —
edge, API, service — are each one careless refactor away from being gone,
and a refactor is not a reviewable event. Removing this one requires a
migration, which is T3 by definition and cannot pass review silently.

DATABASE.md 6.1 and TRD 8.4: these constraints are NOT OPTIONAL and MUST
NOT be removed to simplify a migration. If a migration fails because of
them, the migration is wrong, not the constraint.

One table holds both a Candidate Event and a Verified Record, distinguished
by status. The alternative — promoting rows into a separate table on
decision — was rejected because BR-004 is enforced most strongly when there
is only one write path to guard, and a status transition is a narrower
target than a cross-table copy (DATABASE.md 3.3).
"""

from __future__ import annotations

from alembic import op

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE events (
            -- Server-generated, so an untrusted principal never chooses a
            -- primary-key value (ADR-014).
            id               UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
            -- Client-generated UUIDv7 from the edge. Untrusted input: it is
            -- unique-constrained and used for deduplication, and nothing
            -- else in the schema references it.
            event_id         UUID         NOT NULL,

            -- Denormalised for reporting; kept true by trigger (0008).
            site_id          UUID         NOT NULL
                             REFERENCES sites(id) ON DELETE RESTRICT,
            camera_id        UUID         NOT NULL
                             REFERENCES cameras(id) ON DELETE RESTRICT,
            zone_id          UUID         REFERENCES zones(id) ON DELETE RESTRICT,
            -- SET NULL, not CASCADE: history survives rule deletion.
            rule_id          UUID         REFERENCES detection_rules(id) ON DELETE SET NULL,
            -- The rule AS IT WAS at detection time, written by the edge.
            -- NOT NULL while rule_id is nullable: if the rule is deleted this
            -- is the only remaining record of what actually fired. An audit
            -- requirement, not an optimisation.
            rule_snapshot    JSONB        NOT NULL,

            source           VARCHAR(20)  NOT NULL DEFAULT 'guardian_lens',
            agent_id         UUID         NOT NULL
                             REFERENCES agents(id) ON DELETE RESTRICT,
            model_version_id UUID         REFERENCES model_versions(id) ON DELETE RESTRICT,
            confidence       NUMERIC(4,3),

            -- ADR-007. occurred_at is the edge clock and is what the
            -- reviewer sees; received_at is the control-plane clock and is
            -- what ordering, retention and partitioning use. Both stored,
            -- neither derived from the other.
            occurred_at      TIMESTAMPTZ  NOT NULL,
            received_at      TIMESTAMPTZ  NOT NULL DEFAULT now(),

            evidence_ref     TEXT,
            evidence_state   VARCHAR(20)  NOT NULL DEFAULT 'present',
            evidence_blurred BOOLEAN      NOT NULL DEFAULT FALSE,

            status           VARCHAR(20)  NOT NULL DEFAULT 'unverified',
            reviewer_id      UUID         REFERENCES users(id) ON DELETE RESTRICT,
            decided_at       TIMESTAMPTZ,
            decision_type    VARCHAR(20),
            rejection_reason TEXT,

            version          INTEGER      NOT NULL DEFAULT 1,
            created_at       TIMESTAMPTZ  NOT NULL DEFAULT now(),

            CONSTRAINT uq_events_event_id UNIQUE (event_id),

            ----------------------------------------------------------------
            -- BR-004 and BR-005. Read it in BOTH directions.
            --
            -- Forwards  (BR-005): a decided row MUST carry its reviewer,
            --                     timestamp and decision type.
            -- Backwards (BR-004): an unverified row MUST NOT carry them.
            --                     This forbids pre-filled attribution — a row
            --                     prepared with a reviewer already attached
            --                     and then flipped by something that is not
            --                     the decision path.
            --
            -- The expired branch is tightened against TRD 9.5, which leaves
            -- it bare and so permits an expired row to assert a decision that
            -- by definition never happened: expiry is the terminal state of a
            -- candidate NO reviewer reached in time (AMD-DB-04).
            ----------------------------------------------------------------
            CONSTRAINT chk_decided_requires_reviewer CHECK (
                (status = 'unverified'
                    AND reviewer_id   IS NULL
                    AND decided_at    IS NULL
                    AND decision_type IS NULL)
                OR
                (status IN ('accepted','rejected','corrected')
                    AND reviewer_id   IS NOT NULL
                    AND decided_at    IS NOT NULL
                    AND decision_type IS NOT NULL)
                OR
                (status = 'expired'
                    AND reviewer_id   IS NULL
                    AND decided_at    IS NULL
                    AND decision_type IS NULL)
            ),

            CONSTRAINT chk_rejection_has_reason CHECK (
                status <> 'rejected' OR rejection_reason IS NOT NULL
            ),

            -- VARCHAR + CHECK rather than a native ENUM, deliberately. These
            -- values are rule-bearing: adding 'auto_accepted' would be a
            -- direct BR-004 violation, and it must appear in a migration diff
            -- as an unmistakable rewrite of a named constraint rather than a
            -- one-line ALTER TYPE (DATABASE.md 6.5).
            CONSTRAINT chk_status_valid CHECK (
                status IN ('unverified','accepted','rejected','corrected','expired')
            ),
            CONSTRAINT chk_decision_type_valid CHECK (
                decision_type IS NULL
                OR decision_type IN ('accept','reject','correct')
            ),

            CONSTRAINT chk_source_valid CHECK (source IN ('guardian_lens','nvr')),

            -- BR-D-01: every detection carries the model version that
            -- produced it. The null is permitted exactly where legitimate
            -- and nowhere else — a bare nullable column would also permit a
            -- Guardian Lens event with unreconstructible provenance.
            CONSTRAINT chk_model_version_required CHECK (
                source = 'nvr' OR model_version_id IS NOT NULL
            ),
            CONSTRAINT chk_confidence_required CHECK (
                source = 'nvr' OR confidence IS NOT NULL
            ),

            -- Distinguishes "never captured" from "deleted per retention"
            -- from "storage failed". Without it, an inspector reading a
            -- two-year-old accepted record cannot tell whether the reviewer
            -- saw a frame at all — and those support very different
            -- conclusions about the decision's basis (AMD-DB-12).
            CONSTRAINT chk_evidence_state_coherent CHECK (
                (evidence_state = 'present' AND evidence_ref IS NOT NULL)
                OR (evidence_state IN ('none','deleted','failed')
                    AND evidence_ref IS NULL)
            )
        )
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS events")
