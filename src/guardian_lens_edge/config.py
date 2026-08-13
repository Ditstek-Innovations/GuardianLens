"""Typed agent configuration document — ADR-008, RS-4.

The control plane serves this from ``GET /api/v1/agents/{id}/config``
(TRD 10.6). The TRD does not spell out the response body, so the shape below
is the edge's validation contract, derived from the configuration entities in
DATABASE.md 5.4 (zones carry a normalised polygon; rules carry activation
state, threshold, debounce and dwell). Any document that does not validate is
rejected whole and the last-known-good configuration is retained — never a
default rule set, which would violate BR-001.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

__all__ = ["AgentConfig", "CameraConfig", "RuleConfig", "ZoneConfig"]


class CameraConfig(BaseModel):
    model_config = ConfigDict(frozen=True, extra="allow")

    camera_id: str
    name: str
    sample_rate_fps: float = Field(gt=0, default=2.0)  # TRD 5.2 default 2 fps
    # AES-256-GCM ciphertext of the RTSP URL, base64 in JSON, plus the id
    # of the key that sealed it (BR-S-03: credentials are delivered sealed
    # and decrypted only at the edge, in memory). Optional because the
    # synthetic/dev path has no live camera to describe.
    stream_url_sealed: str | None = None
    stream_url_key_id: str | None = None


class ZoneConfig(BaseModel):
    model_config = ConfigDict(frozen=True, extra="allow")

    zone_id: str
    camera_id: str
    name: str
    # Vertex array [[x, y], ...] in normalised 0-1 space (DATABASE.md 5.4).
    polygon: list[tuple[float, float]] = Field(min_length=3)


class RuleConfig(BaseModel):
    """A detection rule as configured (DATABASE.md 5.4 detection_rules).

    The whole model is snapshotted into every candidate event at detection
    time (ARCHITECTURE.md 6.1 step 6), so it must carry everything a reviewer
    later needs to see what actually fired — including ``human_readable``
    (DP-6).
    """

    model_config = ConfigDict(frozen=True, extra="allow")

    rule_id: str
    zone_id: str
    rule_type: str
    is_active: bool
    confidence_threshold: float = Field(ge=0.0, le=1.0)
    debounce_seconds: int = Field(ge=0)
    dwell_seconds: int | None = Field(default=None, ge=0)
    human_readable: str
    detection_class: str = "person_without_helmet"


class AgentConfig(BaseModel):
    model_config = ConfigDict(frozen=True, extra="allow")

    config_version: int = Field(ge=0)
    site_id: str
    cameras: list[CameraConfig] = Field(default_factory=list)
    zones: list[ZoneConfig] = Field(default_factory=list)
    rules: list[RuleConfig] = Field(default_factory=list)

    def zone_by_id(self, zone_id: str) -> ZoneConfig | None:
        for zone in self.zones:
            if zone.zone_id == zone_id:
                return zone
        return None

    def camera_ids(self) -> list[str]:
        return [camera.camera_id for camera in self.cameras]


def normalise_document(document: object) -> object:
    """Map the control plane's config document onto the edge field names.

    The server exposes resources under ``id`` with the site nested
    (``site: {id, timezone, ...}``); the edge models predate that shape and
    use ``camera_id``/``zone_id``/``rule_id``/``site_id``. TRD 10.6 never
    fixed the document shape, so the adapter lives here at the boundary —
    both shapes validate, and the edge's internals see exactly one.
    """
    if not isinstance(document, dict):
        return document
    doc = dict(document)

    site = doc.pop("site", None)
    if isinstance(site, dict) and "site_id" not in doc:
        if "id" in site:
            doc["site_id"] = site["id"]
        if "timezone" in site and "site_timezone" not in doc:
            doc["site_timezone"] = site["timezone"]

    def _rekey(items: object, key: str) -> object:
        if not isinstance(items, list):
            return items
        out = []
        for item in items:
            if isinstance(item, dict) and "id" in item and key not in item:
                item = dict(item)
                item[key] = item.pop("id")
            out.append(item)
        return out

    doc["cameras"] = _rekey(doc.get("cameras", []), "camera_id")
    doc["zones"] = _rekey(doc.get("zones", []), "zone_id")
    rules = _rekey(doc.get("rules", []), "rule_id")
    # The server ships ONLY active rules — the served set IS the active set
    # (BR-001), so the document carries no is_active field. The edge model
    # keeps it, because scenario/test configs state activation explicitly.
    if isinstance(rules, list):
        rules = [
            {**r, "is_active": True}
            if isinstance(r, dict) and "is_active" not in r
            else r
            for r in rules
        ]
    doc["rules"] = rules
    return doc
