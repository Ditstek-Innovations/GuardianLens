"""Configuration routes — MOD-10 (TRD 10.6).

Role gates per the matrix: sites and cameras are site_admin; zones and
rules are safety_manager (site_admin included). Which SITE a grant covers
is checked in the service against the target object.

POST /cameras/{id}/test is deliberately not implemented: the control
plane makes no outbound requests to user-supplied URLs (TRD 12.6 A10) and
camera URLs are reachable only from the site LAN — connectivity testing
belongs at the edge. Recorded as a gap, not silently skipped.

GET /agents/{id}/config is agent-token only, serves ONLY the agent's own
site, and supports If-None-Match so an unchanged config costs one header
comparison (IF-X1: pull-only with bounded staleness).
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Request, Response

from guardian_lens.api.dependencies.auth import (
    require_agent,
    require_config_role,
    require_site_admin,
)
from guardian_lens.api.dependencies.tenant import get_tenant_context
from guardian_lens.core.errors import ScopeError
from guardian_lens.core.principal import AgentPrincipal, HumanPrincipal
from guardian_lens.repositories.audit import AuditRepository
from guardian_lens.schemas.config import (
    AgentCreate,
    AgentRegisteredResponse,
    AgentResponse,
    CameraCreate,
    CameraPatch,
    CameraResponse,
    ModelVersionCreate,
    ModelVersionResponse,
    RuleCreate,
    RulePatch,
    RuleResponse,
    SiteCreate,
    SiteResponse,
    ZoneCreate,
    ZonePatch,
    ZoneResponse,
)
from guardian_lens.services.audit import AuditService
from guardian_lens.services.configuration import ConfigurationService
from guardian_lens.tenancy.context import TenantContext

router = APIRouter(tags=["config"])


def _service(request: Request, context: TenantContext) -> ConfigurationService:
    return ConfigurationService(
        context,
        AuditService(AuditRepository(context.session)),
        request.app.state.credential_sealer,
    )


def _ip(request: Request) -> str | None:
    return request.client.host if request.client else None


# -- sites -------------------------------------------------------------------


@router.get("/sites", response_model=list[SiteResponse])
def list_sites(
    request: Request,
    principal: HumanPrincipal = Depends(require_site_admin),
    context: TenantContext = Depends(get_tenant_context),
) -> list[SiteResponse]:
    return [
        SiteResponse.model_validate(row._mapping)
        for row in _service(request, context).list_sites(principal)
    ]


@router.post("/sites", response_model=SiteResponse, status_code=201)
def create_site(
    body: SiteCreate,
    request: Request,
    principal: HumanPrincipal = Depends(require_site_admin),
    context: TenantContext = Depends(get_tenant_context),
) -> SiteResponse:
    row = _service(request, context).create_site(
        principal, name=body.name, timezone_name=body.timezone,
        ip_address=_ip(request),
    )
    return SiteResponse.model_validate(row._mapping)


# -- cameras -----------------------------------------------------------------


@router.get("/cameras", response_model=list[CameraResponse])
def list_cameras(
    request: Request,
    principal: HumanPrincipal = Depends(require_site_admin),
    context: TenantContext = Depends(get_tenant_context),
) -> list[CameraResponse]:
    return [
        CameraResponse.model_validate(row._mapping)
        for row in _service(request, context).list_cameras(principal)
    ]


@router.post("/cameras", response_model=CameraResponse, status_code=201)
def create_camera(
    body: CameraCreate,
    request: Request,
    principal: HumanPrincipal = Depends(require_site_admin),
    context: TenantContext = Depends(get_tenant_context),
) -> CameraResponse:
    row = _service(request, context).create_camera(
        principal,
        site_id=body.site_id,
        name=body.name,
        stream_url=body.stream_url,
        location_description=body.location_description,
        stream_profile=body.stream_profile,
        sample_rate_fps=body.sample_rate_fps,
        ip_address=_ip(request),
    )
    return CameraResponse.model_validate(row._mapping)


@router.patch("/cameras/{camera_id}", response_model=CameraResponse)
def patch_camera(
    camera_id: UUID,
    body: CameraPatch,
    request: Request,
    principal: HumanPrincipal = Depends(require_site_admin),
    context: TenantContext = Depends(get_tenant_context),
) -> CameraResponse:
    changes = body.model_dump(exclude_none=True)
    row = _service(request, context).update_camera(
        principal, camera_id, changes, _ip(request)
    )
    return CameraResponse.model_validate(row._mapping)


# -- zones -------------------------------------------------------------------


@router.get("/zones", response_model=list[ZoneResponse])
def list_zones(
    request: Request,
    principal: HumanPrincipal = Depends(require_config_role),
    context: TenantContext = Depends(get_tenant_context),
) -> list[ZoneResponse]:
    return [
        ZoneResponse.model_validate(row._mapping)
        for row in _service(request, context).list_zones(principal)
    ]


@router.post("/zones", response_model=ZoneResponse, status_code=201)
def create_zone(
    body: ZoneCreate,
    request: Request,
    principal: HumanPrincipal = Depends(require_config_role),
    context: TenantContext = Depends(get_tenant_context),
) -> ZoneResponse:
    row = _service(request, context).create_zone(
        principal,
        camera_id=body.camera_id,
        name=body.name,
        polygon=body.polygon,
        ip_address=_ip(request),
    )
    return ZoneResponse.model_validate(row._mapping)


@router.patch("/zones/{zone_id}", response_model=ZoneResponse)
def patch_zone(
    zone_id: UUID,
    body: ZonePatch,
    request: Request,
    principal: HumanPrincipal = Depends(require_config_role),
    context: TenantContext = Depends(get_tenant_context),
) -> ZoneResponse:
    row = _service(request, context).update_zone(
        principal, zone_id, body.model_dump(exclude_none=True), _ip(request)
    )
    return ZoneResponse.model_validate(row._mapping)


@router.delete("/zones/{zone_id}", status_code=204)
def delete_zone(
    zone_id: UUID,
    request: Request,
    principal: HumanPrincipal = Depends(require_config_role),
    context: TenantContext = Depends(get_tenant_context),
) -> Response:
    _service(request, context).delete_zone(principal, zone_id, _ip(request))
    return Response(status_code=204)


# -- detection rules ---------------------------------------------------------


@router.get("/rules", response_model=list[RuleResponse])
def list_rules(
    request: Request,
    principal: HumanPrincipal = Depends(require_config_role),
    context: TenantContext = Depends(get_tenant_context),
) -> list[RuleResponse]:
    return [
        RuleResponse.model_validate(row._mapping)
        for row in _service(request, context).list_rules(principal)
    ]


@router.post("/rules", response_model=RuleResponse, status_code=201)
def create_rule(
    body: RuleCreate,
    request: Request,
    principal: HumanPrincipal = Depends(require_config_role),
    context: TenantContext = Depends(get_tenant_context),
) -> RuleResponse:
    row = _service(request, context).create_rule(
        principal,
        zone_id=body.zone_id,
        rule_type=body.rule_type,
        confidence_threshold=body.confidence_threshold,
        debounce_seconds=body.debounce_seconds,
        dwell_seconds=body.dwell_seconds,
        human_readable=body.human_readable,
        written_rule_reference=body.written_rule_reference,
        detection_class=body.detection_class,
        must_be_carried=body.must_be_carried,
        ip_address=_ip(request),
    )
    return RuleResponse.model_validate(row._mapping)


@router.patch("/rules/{rule_id}", response_model=RuleResponse)
def patch_rule(
    rule_id: UUID,
    body: RulePatch,
    request: Request,
    principal: HumanPrincipal = Depends(require_config_role),
    context: TenantContext = Depends(get_tenant_context),
) -> RuleResponse:
    row = _service(request, context).update_rule(
        principal, rule_id, body.model_dump(exclude_none=True), _ip(request)
    )
    return RuleResponse.model_validate(row._mapping)


@router.post("/rules/{rule_id}/activate", response_model=RuleResponse)
def activate_rule(
    rule_id: UUID,
    request: Request,
    principal: HumanPrincipal = Depends(require_config_role),
    context: TenantContext = Depends(get_tenant_context),
) -> RuleResponse:
    # Explicit activation — BR-001/BR-C-02. The activator is the token's
    # principal; the request carries no body at all.
    row = _service(request, context).activate_rule(
        principal, rule_id, _ip(request)
    )
    return RuleResponse.model_validate(row._mapping)


# -- edge agent principals (WORKFLOW.md 7 gap 1) -----------------------------


@router.get("/agents", response_model=list[AgentResponse])
def list_agents(
    request: Request,
    principal: HumanPrincipal = Depends(require_site_admin),
    context: TenantContext = Depends(get_tenant_context),
) -> list[AgentResponse]:
    return [
        AgentResponse.model_validate(row._mapping)
        for row in _service(request, context).list_agents(principal)
    ]


@router.post("/agents", response_model=AgentRegisteredResponse, status_code=201)
def register_agent(
    body: AgentCreate,
    request: Request,
    principal: HumanPrincipal = Depends(require_site_admin),
    context: TenantContext = Depends(get_tenant_context),
) -> AgentRegisteredResponse:
    # The composite credential appears in THIS response and nowhere else —
    # not in the audit state, not in a log line, not on any later read.
    row, credential = _service(request, context).register_agent(
        principal, site_id=body.site_id, name=body.name, ip_address=_ip(request)
    )
    return AgentRegisteredResponse.model_validate(
        {**row._mapping, "credential": credential}
    )


# -- model versions (gate G1 evidence trail) ---------------------------------


@router.get("/model-versions", response_model=list[ModelVersionResponse])
def list_model_versions(
    request: Request,
    principal: HumanPrincipal = Depends(require_site_admin),
    context: TenantContext = Depends(get_tenant_context),
) -> list[ModelVersionResponse]:
    return [
        ModelVersionResponse.model_validate(row._mapping)
        for row in _service(request, context).list_model_versions(principal)
    ]


@router.post("/model-versions", response_model=ModelVersionResponse, status_code=201)
def register_model_version(
    body: ModelVersionCreate,
    request: Request,
    principal: HumanPrincipal = Depends(require_site_admin),
    context: TenantContext = Depends(get_tenant_context),
) -> ModelVersionResponse:
    row = _service(request, context).register_model_version(
        principal,
        version=body.version,
        artefact_hash=body.artefact_hash,
        classes=body.classes,
        training_data_hash=body.training_data_hash,
        model_card_ref=body.model_card_ref,
        datasheet_ref=body.datasheet_ref,
        notes=body.notes,
        ip_address=_ip(request),
    )
    return ModelVersionResponse.model_validate(row._mapping)


@router.post(
    "/model-versions/{model_version_id}/approve",
    response_model=ModelVersionResponse,
)
def approve_model_version(
    model_version_id: UUID,
    request: Request,
    principal: HumanPrincipal = Depends(require_site_admin),
    context: TenantContext = Depends(get_tenant_context),
) -> ModelVersionResponse:
    # Explicit approval, approver from the token — the BR-C-02 pattern
    # applied to gate G1; the request carries no body at all.
    row = _service(request, context).approve_model_version(
        principal, model_version_id, _ip(request)
    )
    return ModelVersionResponse.model_validate(row._mapping)


# -- agent config pull -------------------------------------------------------


@router.get("/agents/{agent_id}/config")
def agent_config(
    agent_id: UUID,
    request: Request,
    response: Response,
    agent: AgentPrincipal = Depends(require_agent),
    context: TenantContext = Depends(get_tenant_context),
    if_none_match: str | None = Header(default=None),
) -> Any:
    # An agent may pull ITS OWN configuration only. The path id must match
    # the token — the path is addressing, the token is authority.
    if agent_id != agent.agent_id:
        raise ScopeError("an agent may only pull its own configuration")

    document = _service(request, context).agent_config(agent.site_id)
    etag = f'"{document["config_version"]}"'
    response.headers["ETag"] = etag
    if if_none_match is not None and if_none_match.strip() == etag:
        return Response(status_code=304, headers={"ETag": etag})
    return document
