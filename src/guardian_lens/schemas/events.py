"""Ingest and review schemas — TRD 10.3, 10.4."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class EvidencePayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    content_type: Literal["image/jpeg"]
    blurred: bool = False
    data_b64: str


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
    occurred_at: datetime
    evidence: EvidencePayload | None = None


class IngestResponse(BaseModel):
    id: UUID
    event_id: UUID
    status: str
    received_at: datetime


class AgentHealthRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    # The agent's clock at send time; skew = receive - send (ADR-007).
    sent_at: datetime
    applied_config_version: int | None = None
    agent_version: str | None = Field(default=None, max_length=40)


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


class QueueResponse(BaseModel):
    items: list[QueueItem]
    # On every queue response so the UI honours DP-4 without a second
    # request (TRD 10.4).
    queue_depth: int
    next_cursor: str | None


class EventDetail(BaseModel):
    id: UUID
    event_id: UUID
    camera_id: UUID
    zone_id: UUID | None
    rule_id: UUID | None
    rule_snapshot: dict[str, Any]
    source: str
    confidence: float | None
    occurred_at: datetime
    received_at: datetime
    status: str
    evidence_url: str | None
    evidence_state: str
    decision_type: str | None
    rejection_reason: str | None
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
    corrections: list[CorrectionItem] | None = None


class DecisionReviewer(BaseModel):
    id: UUID
    full_name: str


class DecisionResponse(BaseModel):
    id: UUID
    status: str
    reviewer: DecisionReviewer
    decided_at: datetime
    decision_type: str
    version: int
