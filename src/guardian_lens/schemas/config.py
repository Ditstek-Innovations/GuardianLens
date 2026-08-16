"""Configuration schemas — TRD 10.6.

Camera responses: there is deliberately NO field through which a stream
URL — plaintext or sealed — could travel to a human client. The sealed
credential appears only in the agent config document (a dict built by the
repository, delivered on an agent-token-only route), because credentials
are decrypted only at the edge (ARCHITECTURE.md 8.10).
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class SiteCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=200)
    timezone: str = Field(min_length=1, max_length=64)


class SiteResponse(BaseModel):
    id: UUID
    name: str
    timezone: str
    config_version: int
    created_at: datetime


class CameraCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    site_id: UUID
    name: str = Field(min_length=1, max_length=200)
    # Accepted ONCE, sealed immediately, never returned, never logged.
    stream_url: str = Field(min_length=1, max_length=2000)
    location_description: str | None = Field(default=None, max_length=2000)
    stream_profile: Literal["primary", "secondary"] = "secondary"
    sample_rate_fps: float = Field(default=2.0, gt=0, le=30)


class CameraPatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, min_length=1, max_length=200)
    stream_url: str | None = Field(default=None, min_length=1, max_length=2000)
    location_description: str | None = Field(default=None, max_length=2000)
    stream_profile: Literal["primary", "secondary"] | None = None
    sample_rate_fps: float | None = Field(default=None, gt=0, le=30)
    status: Literal["active", "degraded", "disconnected", "disabled"] | None = None


class CameraResponse(BaseModel):
    id: UUID
    site_id: UUID
    name: str
    location_description: str | None
    stream_profile: str
    sample_rate_fps: Decimal
    status: str
    created_at: datetime
    updated_at: datetime


class ZoneCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    camera_id: UUID
    name: str = Field(min_length=1, max_length=200)
    # Normalised 0–1 vertex space, so a zone survives a resolution change.
    polygon: list[list[float]] = Field(min_length=3)


class ZonePatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, min_length=1, max_length=200)
    polygon: list[list[float]] | None = Field(default=None, min_length=3)


class ZoneResponse(BaseModel):
    id: UUID
    camera_id: UUID
    name: str
    polygon: list[list[float]]
    created_at: datetime
    updated_at: datetime


class RuleCreate(BaseModel):
    """No is_active field: a rule cannot be created active (BR-001)."""

    model_config = ConfigDict(extra="forbid")

    zone_id: UUID
    rule_type: str = Field(min_length=1, max_length=50)
    confidence_threshold: float = Field(ge=0.0, le=1.0)
    debounce_seconds: int = Field(ge=0)
    dwell_seconds: int | None = Field(default=None, ge=0)
    human_readable: str = Field(min_length=1, max_length=2000)
    written_rule_reference: str | None = Field(default=None, max_length=2000)
    # The model-output class name this rule watches for (ARCHITECTURE.md
    # 6.1 D1 evaluator). Defaults to the original ppe_helmet trigger so
    # every rule created before this field existed keeps working unchanged.
    detection_class: str = Field(
        default="person_without_helmet", min_length=1, max_length=100
    )
    # Held-vs-lying discriminator: fire only when the condition's box sits
    # inside a detected person's box (frame geometry at the edge, BR-D-03).
    must_be_carried: bool = False


class RulePatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    confidence_threshold: float | None = Field(default=None, ge=0.0, le=1.0)
    debounce_seconds: int | None = Field(default=None, ge=0)
    dwell_seconds: int | None = Field(default=None, ge=0)
    human_readable: str | None = Field(default=None, min_length=1, max_length=2000)
    written_rule_reference: str | None = Field(default=None, max_length=2000)
    detection_class: str | None = Field(default=None, min_length=1, max_length=100)
    must_be_carried: bool | None = None
    # An is_active flip is routed through the explicit activation /
    # deactivation path, which records the named activator (BR-C-02).
    is_active: bool | None = None


class RuleResponse(BaseModel):
    id: UUID
    zone_id: UUID
    rule_type: str
    is_active: bool
    confidence_threshold: Decimal
    debounce_seconds: int
    dwell_seconds: int | None
    human_readable: str
    written_rule_reference: str | None
    detection_class: str
    must_be_carried: bool
    created_by: UUID
    activated_by: UUID | None
    activated_at: datetime | None
    deactivated_at: datetime | None
    created_at: datetime
    updated_at: datetime


class AgentCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    site_id: UUID
    name: str = Field(min_length=1, max_length=200)


class AgentResponse(BaseModel):
    """No credential material, ever — credential_hash has no response field
    through which it could travel (mirrors the camera credential rule)."""

    id: UUID
    site_id: UUID
    name: str
    status: str
    last_seen_at: datetime | None
    last_health_at: datetime | None
    agent_version: str | None
    applied_config_version: int | None
    clock_skew_ms: int | None


class AgentRegisteredResponse(AgentResponse):
    """Registration only. The composite credential (slug:agent_id:secret,
    the /auth/agent exchange format) is returned exactly ONCE, here; the
    server stores an Argon2 hash and cannot reproduce it."""

    credential: str


class ModelVersionCreate(BaseModel):
    """Gate G1 evidence trail (GOVERNANCE.md 9): registration records the
    artefact identity and the card/datasheet references. There is no
    deployed_at field — deployment requires a recorded approval first
    (chk_model_deployed_requires_approval, migration 0004)."""

    model_config = ConfigDict(extra="forbid")

    version: str = Field(min_length=1, max_length=40)
    artefact_hash: str = Field(min_length=1, max_length=200)
    classes: list[str] = Field(min_length=1)
    training_data_hash: str | None = Field(default=None, max_length=200)
    model_card_ref: str | None = Field(default=None, max_length=2000)
    datasheet_ref: str | None = Field(default=None, max_length=2000)
    notes: str | None = Field(default=None, max_length=4000)


class ModelVersionResponse(BaseModel):
    id: UUID
    version: str
    artefact_hash: str
    training_data_hash: str | None
    classes: list[str]
    model_card_ref: str | None
    datasheet_ref: str | None
    approved_by: UUID | None
    approved_at: datetime | None
    deployed_at: datetime | None
    notes: str | None
