"""Ingest and review schemas — TRD 10.3, 10.4."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class EvidencePayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    content_type: Literal["image/jpeg"]
    blurred: bool = False
    data_b64: str


class DetectionPrediction(BaseModel):
    """Structured model output retained for review feedback and training."""

    model_config = ConfigDict(extra="forbid")

    class_name: str = Field(min_length=1, max_length=100)
    bbox_norm: tuple[
        float,
        float,
        float,
        float,
    ]

    @field_validator("bbox_norm")
    @classmethod
    def validate_bbox(
        cls, value: tuple[float, float, float, float]
    ) -> tuple[float, float, float, float]:
        x1, y1, x2, y2 = value
        if not all(0.0 <= coordinate <= 1.0 for coordinate in value):
            raise ValueError("bbox_norm coordinates must be between 0 and 1")
        if x2 <= x1 or y2 <= y1:
            raise ValueError("bbox_norm must have positive width and height")
        return value


class EventIngestRequest(BaseModel):
    """TRD 10.3. status, reviewer_id and decided_at are ABSENT by design;
    extra="forbid" rejects the rest of the unknown universe, and the
    controller's raw-body guard turns those three into the rule's 400."""

    model_config = ConfigDict(extra="forbid")

    event_id: UUID
    camera_id: UUID
    zone_id: UUID | None = None
    rule_id: UUID | None = None
    rule_snapshot: dict[str, Any]
    source: Literal["guardian_lens", "nvr"] = "guardian_lens"
    model_version: str | None = Field(default=None, max_length=40)
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    prediction: DetectionPrediction | None = None
    occurred_at: datetime
    evidence: EvidencePayload | None = None


class IngestResponse(BaseModel):
    id: UUID
    event_id: UUID
    status: str
    received_at: datetime


class CameraReviewBlock(BaseModel):
    """Why this camera has not produced a Review item (latest sample)."""

    model_config = ConfigDict(extra="forbid")

    camera_id: UUID
    stream: Literal["online", "down"]
    last_seen_classes: list[str] = Field(default_factory=list, max_length=24)
    watched_classes: list[str] = Field(default_factory=list, max_length=24)
    why_not_review: list[str] = Field(default_factory=list, max_length=8)
    matched: bool = False
    observed_at: datetime | None = None


class AgentHealthRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    # The agent's clock at send time; skew = receive - send (ADR-007).
    sent_at: datetime
    applied_config_version: int | None = None
    agent_version: str | None = Field(default=None, max_length=40)
    # Latest per-camera miss snapshot for the Review empty state. Optional
    # so older agents keep working.
    review_block: list[CameraReviewBlock] | None = Field(default=None, max_length=64)


class ReviewBlockItem(BaseModel):
    """Queue-facing copy of CameraReviewBlock plus the camera name."""

    camera_id: UUID
    camera_name: str
    stream: str
    last_seen_classes: list[str]
    watched_classes: list[str]
    why_not_review: list[str]
    matched: bool
    observed_at: datetime | None = None


class AgentHealthResponse(BaseModel):
    status: str = "ok"
    clock_skew_ms: int


class CoverageGapRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID  # edge-generated — the idempotency key
    camera_id: UUID | None = None
    started_at: datetime
    ended_at: datetime | None = None
    reason: Literal["stream_lost", "inference_failure", "agent_down", "outbox_full"]
    detail: str | None = Field(default=None, max_length=2000)


class QueueCamera(BaseModel):
    id: UUID
    name: str


class QueueZone(BaseModel):
    id: UUID | None
    name: str | None


class QueueRule(BaseModel):
    human_readable: str | None


class CorrectionChoice(BaseModel):
    id: UUID
    name: str


class CorrectionOptionsResponse(BaseModel):
    zones: list[CorrectionChoice]
    rules: list[CorrectionChoice]


class QueueItem(BaseModel):
    id: UUID
    camera: QueueCamera
    zone: QueueZone
    rule: QueueRule
    source: str
    confidence: float | None
    occurred_at: datetime
    status: str
    evidence_url: str | None
    version: int
    # FR-013 — which model produced the detection; None for nvr-sourced.
    model_version: str | None = None
    # NFR-L-02 — timestamps render in the site's clock; viewer-local only
    # when a site zone is genuinely absent.
    site_timezone: str | None = None


class QueueResponse(BaseModel):
    items: list[QueueItem]
    # On every queue response so the UI honours DP-4 without a second
    # request (TRD 10.4).
    queue_depth: int
    next_cursor: str | None
    why_not_review: list[ReviewBlockItem] = Field(default_factory=list)


class DecisionReviewer(BaseModel):
    id: UUID
    full_name: str


class IncidentGroup(BaseModel):
    """One ongoing condition, shown as one queue row.

    Display grouping ONLY: `event_ids` are the members, each of which is
    decided individually through the normal single-event decision route —
    there is no incident-level decision anywhere (BR-V-02)."""

    incident_key: UUID  # id of the oldest member; stable while it exists
    camera: QueueCamera
    zone: QueueZone
    rule: QueueRule
    count: int
    first_occurred_at: datetime
    last_occurred_at: datetime
    max_confidence: float | None
    status: str
    site_timezone: str | None
    event_ids: list[UUID]


class IncidentQueueResponse(BaseModel):
    incidents: list[IncidentGroup]
    queue_depth: int
    gap_seconds: int
    # True when the grouping scan hit its row cap: counts may be partial.
    # Surfaced, never silent.
    capped: bool
    why_not_review: list[ReviewBlockItem] = Field(default_factory=list)


class EventDetail(BaseModel):
    id: UUID
    event_id: UUID
    camera_id: UUID
    camera: QueueCamera
    zone_id: UUID | None
    zone: QueueZone
    rule_id: UUID | None
    rule: QueueRule
    rule_snapshot: dict[str, Any]
    source: str
    confidence: float | None
    predicted_class: str | None = None
    predicted_bbox: list[float] | None = None
    occurred_at: datetime
    received_at: datetime
    status: str
    evidence_url: str | None
    evidence_state: str
    decision_type: str | None
    rejection_reason: str | None
    # BR-005 — a decided event carries its reviewer and timestamp; both are
    # None exactly while status is 'unverified'.
    reviewer: DecisionReviewer | None
    decided_at: datetime | None
    site_timezone: str | None
    version: int


class CorrectionItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    field: str = Field(max_length=64)
    value: str = Field(max_length=200)


class DecisionRequest(BaseModel):
    """TRD 10.4. reviewer_id has no field here and never will — identity
    comes from the token only (BR-S-01)."""

    model_config = ConfigDict(extra="forbid")

    decision: Literal["accept", "reject", "correct"]
    version: int = Field(ge=1)
    rejection_reason: str | None = Field(default=None, max_length=2000)
    training_feedback: Literal["false_positive", "exclude"] | None = None
    corrections: list[CorrectionItem] | None = None


class DecisionResponse(BaseModel):
    id: UUID
    status: str
    reviewer: DecisionReviewer
    decided_at: datetime
    decision_type: str
    version: int
