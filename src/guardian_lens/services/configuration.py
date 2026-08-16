"""ConfigurationService — MOD-10: sites, cameras, zones, rules.

Every mutation and its audit entry share ONE transaction (BR-C-01): a
configuration change that cannot be audited must not take effect. Every
mutation inside a site also bumps that site's config_version, so the
pull-only agent config (IF-X1, ADR-008) observes exactly the committed
changes.

Camera credentials: stream_url arrives once, is sealed immediately by the
CredentialSealer, and the plaintext is dropped. It appears in no response
schema, no audit state (AuditWriteGuard would refuse it) and no log line
(BR-S-03).

Rule lifecycle: created inactive, always (BR-001); activation is a
separate, explicit act that records the named activator (BR-C-02) —
whether it arrives via POST /rules/{id}/activate or via PATCH
{is_active: true}, the same service path runs.
"""

from __future__ import annotations

import secrets
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

import sqlalchemy as sa
from argon2 import PasswordHasher

from guardian_lens.core.errors import (
    DuplicateResourceError,
    NotFoundError,
    ScopeError,
    ValidationFailureError,
)
from guardian_lens.core.principal import HumanPrincipal
from guardian_lens.guards.default_off import DefaultOffGuard
from guardian_lens.repositories.config import ConfigRepository
from guardian_lens.repositories.identity import IdentityRepository
from guardian_lens.services.audit import AuditService
from guardian_lens.services.sealer import CredentialSealer
from guardian_lens.tenancy.context import TenantContext

__all__ = ["ConfigurationService"]

_ZONE_NOT_FOUND = "zone not found"
_RULE_NOT_FOUND = "rule not found"

# Argon2id, the same scheme agent_login verifies against (services/identity).
_credential_hasher = PasswordHasher()


class ConfigurationService:
    def __init__(
        self,
        context: TenantContext,
        audit: AuditService,
        sealer: CredentialSealer,
    ) -> None:
        self._session = context.session
        self._config = ConfigRepository(context.session)
        self._audit = audit
        self._sealer = sealer
        self._tenant_slug = context.tenant_slug

    # -- sites ---------------------------------------------------------------

    def create_site(
        self, principal: HumanPrincipal, *, name: str, timezone_name: str,
        ip_address: str | None,
    ) -> sa.Row:
        site = self._config.insert_site({"name": name, "timezone": timezone_name})
        self._audit.write(
            action="site.created",
            entity_type="site",
            actor_user_id=principal.user_id,
            entity_id=site.id,
            after_state={"name": name, "timezone": timezone_name},
            ip_address=ip_address,
        )
        # The creator receives site_admin at the new site, in the same
        # transaction. Roles are site-scoped (TRD 12.3) and user management
        # is [V1] (TRD 10.6), so without this grant a newly created site
        # would be manageable by no one — an orphan by construction.
        IdentityRepository(self._session).grant_role(
            user_id=principal.user_id,
            role_name="site_admin",
            site_id=site.id,
            granted_by=principal.user_id,
        )
        self._audit.write(
            action="user.role_granted",
            entity_type="user_role",
            actor_user_id=principal.user_id,
            entity_key=f"{principal.user_id}:site_admin:{site.id}",
            after_state={"role": "site_admin", "site_id": str(site.id)},
            ip_address=ip_address,
        )
        self._session.commit()
        return site

    def list_sites(self, principal: HumanPrincipal) -> list[sa.Row]:
        return list(self._config.list_sites(sorted(principal.site_ids())))

    # -- cameras -------------------------------------------------------------

    def create_camera(
        self,
        principal: HumanPrincipal,
        *,
        site_id: UUID,
        name: str,
        stream_url: str,
        location_description: str | None,
        stream_profile: str,
        sample_rate_fps: float,
        ip_address: str | None,
    ) -> sa.Row:
        self._ensure_site_scope(principal, site_id)
        # Seal immediately; the plaintext does not outlive this frame.
        sealed = self._sealer.seal(stream_url)
        camera = self._config.insert_camera(
            {
                "site_id": site_id,
                "name": name,
                "location_description": location_description,
                "stream_url_encrypted": sealed,
                "stream_url_key_id": self._sealer.key_id,
                "stream_profile": stream_profile,
                "sample_rate_fps": sample_rate_fps,
            }
        )
        self._audit.write(
            action="camera.created",
            entity_type="camera",
            actor_user_id=principal.user_id,
            entity_id=camera.id,
            # Allowlisted fields only — never the credential
            # (DATABASE.md 10.3).
            after_state={
                "site_id": str(site_id),
                "name": name,
                "stream_profile": stream_profile,
                "stream_url_key_id": self._sealer.key_id,
            },
            ip_address=ip_address,
        )
        self._config.bump_config_version(site_id)
        self._session.commit()
        return camera

    def list_cameras(self, principal: HumanPrincipal) -> list[sa.Row]:
        return list(self._config.list_cameras(sorted(principal.site_ids())))

    def update_camera(
        self,
        principal: HumanPrincipal,
        camera_id: UUID,
        changes: dict[str, Any],
        ip_address: str | None,
    ) -> sa.Row:
        before = self._config.get_camera(camera_id)
        if before is None:
            raise NotFoundError("camera not found")
        self._ensure_site_scope(principal, before.site_id)

        values = dict(changes)
        stream_url = values.pop("stream_url", None)
        if stream_url is not None:
            values["stream_url_encrypted"] = self._sealer.seal(stream_url)
            values["stream_url_key_id"] = self._sealer.key_id
        if not values and stream_url is None:
            raise ValidationFailureError("no fields to update")

        camera = self._config.update_camera(camera_id, values)
        auditable = {
            k: str(v) for k, v in changes.items() if k != "stream_url"
        }
        if stream_url is not None:
            # Record THAT the credential changed, never what it is.
            auditable["stream_url_key_id"] = self._sealer.key_id
        self._audit.write(
            action="camera.updated",
            entity_type="camera",
            actor_user_id=principal.user_id,
            entity_id=camera_id,
            before_state={
                k: str(getattr(before, k))
                for k in auditable
                if k != "stream_url_key_id" and hasattr(before, k)
            },
            after_state=auditable,
            ip_address=ip_address,
        )
        self._config.bump_config_version(before.site_id)
        self._session.commit()
        return camera  # type: ignore[return-value]

    # -- zones ---------------------------------------------------------------

    def create_zone(
        self,
        principal: HumanPrincipal,
        *,
        camera_id: UUID,
        name: str,
        polygon: list[list[float]],
        ip_address: str | None,
    ) -> sa.Row:
        site_id = self._config.camera_site(camera_id)
        if site_id is None:
            raise NotFoundError("camera not found")
        self._ensure_site_scope(principal, site_id)
        zone = self._config.insert_zone(
            {"camera_id": camera_id, "name": name, "polygon": polygon}
        )
        self._audit.write(
            action="zone.created",
            entity_type="zone",
            actor_user_id=principal.user_id,
            entity_id=zone.id,
            after_state={
                "camera_id": str(camera_id), "name": name, "polygon": polygon
            },
            ip_address=ip_address,
        )
        self._config.bump_config_version(site_id)
        self._session.commit()
        return zone

    def list_zones(self, principal: HumanPrincipal) -> list[sa.Row]:
        return list(self._config.list_zones(sorted(principal.site_ids())))

    def update_zone(
        self,
        principal: HumanPrincipal,
        zone_id: UUID,
        changes: dict[str, Any],
        ip_address: str | None,
    ) -> sa.Row:
        site_id = self._config.zone_site(zone_id)
        if site_id is None:
            raise NotFoundError(_ZONE_NOT_FOUND)
        self._ensure_site_scope(principal, site_id)
        before = self._config.get_zone(zone_id)
        zone = self._config.update_zone(zone_id, changes)
        self._audit.write(
            action="zone.updated",
            entity_type="zone",
            actor_user_id=principal.user_id,
            entity_id=zone_id,
            before_state={
                k: before._mapping[k] if k == "polygon"  # type: ignore[union-attr]
                else str(before._mapping[k])  # type: ignore[union-attr]
                for k in changes
            },
            after_state={
                k: v if k == "polygon" else str(v) for k, v in changes.items()
            },
            ip_address=ip_address,
        )
        self._config.bump_config_version(site_id)
        self._session.commit()
        return zone  # type: ignore[return-value]

    def delete_zone(
        self, principal: HumanPrincipal, zone_id: UUID, ip_address: str | None
    ) -> None:
        site_id = self._config.zone_site(zone_id)
        if site_id is None:
            raise NotFoundError(_ZONE_NOT_FOUND)
        self._ensure_site_scope(principal, site_id)
        before = self._config.get_zone(zone_id)
        self._config.delete_zone(zone_id)
        self._audit.write(
            action="zone.deleted",
            entity_type="zone",
            actor_user_id=principal.user_id,
            entity_id=zone_id,
            before_state={"name": before.name, "polygon": before.polygon},  # type: ignore[union-attr]
            ip_address=ip_address,
        )
        self._config.bump_config_version(site_id)
        self._session.commit()

    # -- detection rules -----------------------------------------------------

    def create_rule(
        self,
        principal: HumanPrincipal,
        *,
        zone_id: UUID,
        rule_type: str,
        confidence_threshold: float,
        debounce_seconds: int,
        dwell_seconds: int | None,
        human_readable: str,
        written_rule_reference: str | None,
        detection_class: str,
        ip_address: str | None,
    ) -> sa.Row:
        site_id = self._config.zone_site(zone_id)
        if site_id is None:
            raise NotFoundError(_ZONE_NOT_FOUND)
        self._ensure_site_scope(principal, site_id)

        # BR-001: no creation path produces an active rule. The schema does
        # not accept is_active at all; the guard states the invariant.
        DefaultOffGuard.ensure_created_inactive(False)
        rule = self._config.insert_rule(
            {
                "zone_id": zone_id,
                "rule_type": rule_type,
                "confidence_threshold": confidence_threshold,
                "debounce_seconds": debounce_seconds,
                "dwell_seconds": dwell_seconds,
                "human_readable": human_readable,
                "written_rule_reference": written_rule_reference,
                "detection_class": detection_class,
                "created_by": principal.user_id,
            }
        )
        self._audit.write(
            action="rule.created",
            entity_type="rule",
            actor_user_id=principal.user_id,
            entity_id=rule.id,
            after_state={
                "zone_id": str(zone_id),
                "rule_type": rule_type,
                "is_active": False,
                "confidence_threshold": confidence_threshold,
                "debounce_seconds": debounce_seconds,
                "human_readable": human_readable,
                "detection_class": detection_class,
            },
            ip_address=ip_address,
        )
        self._config.bump_config_version(site_id)
        self._session.commit()
        return rule

    def list_rules(self, principal: HumanPrincipal) -> list[sa.Row]:
        return list(self._config.list_rules(sorted(principal.site_ids())))

    def activate_rule(
        self, principal: HumanPrincipal, rule_id: UUID, ip_address: str | None
    ) -> sa.Row:
        """Explicit activation — BR-C-02. activated_by comes from the
        token; there is no parameter for it."""
        site_id = self._config.rule_site(rule_id)
        if site_id is None:
            raise NotFoundError(_RULE_NOT_FOUND)
        self._ensure_site_scope(principal, site_id)
        before = self._config.get_rule(rule_id)

        activated_at = datetime.now(timezone.utc)
        DefaultOffGuard.ensure_named_activator(principal.user_id, activated_at)
        rule = self._config.update_rule(
            rule_id,
            {
                "is_active": True,
                "activated_by": principal.user_id,
                "activated_at": activated_at,
                "deactivated_at": None,
            },
        )
        self._audit.write(
            action="rule.activated",
            entity_type="rule",
            actor_user_id=principal.user_id,
            entity_id=rule_id,
            before_state={
                "is_active": before.is_active,  # type: ignore[union-attr]
                "confidence_threshold": float(before.confidence_threshold),  # type: ignore[union-attr]
                "debounce_seconds": before.debounce_seconds,  # type: ignore[union-attr]
            },
            after_state={
                "is_active": True,
                "activated_by": str(principal.user_id),
                "activated_at": activated_at.isoformat(),
            },
            ip_address=ip_address,
        )
        self._config.bump_config_version(site_id)
        self._session.commit()
        return rule  # type: ignore[return-value]

    def update_rule(
        self,
        principal: HumanPrincipal,
        rule_id: UUID,
        changes: dict[str, Any],
        ip_address: str | None,
    ) -> sa.Row:
        """PATCH. An is_active flip routes through the activation /
        deactivation paths so attribution can never be skipped."""
        is_active = changes.pop("is_active", None)
        if is_active is True:
            if changes:
                raise ValidationFailureError(
                    "activate a rule in its own request; combining activation "
                    "with other changes obscures what was approved",
                    field="is_active",
                )
            return self.activate_rule(principal, rule_id, ip_address)
        if is_active is False:
            if changes:
                raise ValidationFailureError(
                    "deactivate a rule in its own request", field="is_active"
                )
            return self.deactivate_rule(principal, rule_id, ip_address)

        site_id = self._config.rule_site(rule_id)
        if site_id is None:
            raise NotFoundError(_RULE_NOT_FOUND)
        self._ensure_site_scope(principal, site_id)
        if not changes:
            raise ValidationFailureError("no fields to update")
        before = self._config.get_rule(rule_id)
        rule = self._config.update_rule(rule_id, changes)
        self._audit.write(
            action="rule.updated",
            entity_type="rule",
            actor_user_id=principal.user_id,
            entity_id=rule_id,
            before_state={k: str(before._mapping[k]) for k in changes},  # type: ignore[union-attr]
            after_state={k: str(v) for k, v in changes.items()},
            ip_address=ip_address,
        )
        self._config.bump_config_version(site_id)
        self._session.commit()
        return rule  # type: ignore[return-value]

    def deactivate_rule(
        self, principal: HumanPrincipal, rule_id: UUID, ip_address: str | None
    ) -> sa.Row:
        site_id = self._config.rule_site(rule_id)
        if site_id is None:
            raise NotFoundError(_RULE_NOT_FOUND)
        self._ensure_site_scope(principal, site_id)
        before = self._config.get_rule(rule_id)
        rule = self._config.update_rule(
            rule_id,
            {"is_active": False, "deactivated_at": datetime.now(timezone.utc)},
        )
        self._audit.write(
            action="rule.deactivated",
            entity_type="rule",
            actor_user_id=principal.user_id,
            entity_id=rule_id,
            before_state={"is_active": before.is_active},  # type: ignore[union-attr]
            after_state={"is_active": False},
            ip_address=ip_address,
        )
        self._config.bump_config_version(site_id)
        self._session.commit()
        return rule  # type: ignore[return-value]

    # -- edge agents (WORKFLOW.md 7 gap 1) -----------------------------------

    def register_agent(
        self,
        principal: HumanPrincipal,
        *,
        site_id: UUID,
        name: str,
        ip_address: str | None,
    ) -> tuple[sa.Row, str]:
        """Register an edge agent principal at one site.

        Returns the row and the composite credential ``slug:agent_id:secret``
        — the /auth/agent exchange format — exactly once. Only the Argon2
        hash is stored; the server cannot reproduce the secret afterwards.
        An agent principal can never hold a review role (BR-S-02, 0003:
        the grant relation does not exist).
        """
        self._ensure_site_scope(principal, site_id)
        secret = secrets.token_hex(24)
        agent = self._config.insert_agent(
            {
                "site_id": site_id,
                "name": name,
                "credential_hash": _credential_hasher.hash(secret),
            }
        )
        self._audit.write(
            action="agent.registered",
            entity_type="agent",
            actor_user_id=principal.user_id,
            entity_id=agent.id,
            # Allowlisted fields only — never credential material
            # (DATABASE.md 10.4).
            after_state={
                "site_id": str(site_id),
                "name": name,
                "status": agent.status,
            },
            ip_address=ip_address,
        )
        self._session.commit()
        return agent, f"{self._tenant_slug}:{agent.id}:{secret}"

    def list_agents(self, principal: HumanPrincipal) -> list[sa.Row]:
        return list(self._config.list_agents(sorted(principal.site_ids())))

    # -- model versions (gate G1 evidence trail) -----------------------------

    def register_model_version(
        self,
        principal: HumanPrincipal,
        *,
        version: str,
        artefact_hash: str,
        classes: list[str],
        training_data_hash: str | None,
        model_card_ref: str | None,
        datasheet_ref: str | None,
        notes: str | None,
        ip_address: str | None,
    ) -> sa.Row:
        """Record a model version and its G1 evidence references.

        Registration is not deployment: deployed_at stays NULL and cannot be
        set without a recorded approval (chk_model_deployed_requires_approval,
        0004). Versions are immutable identity — a duplicate is a conflict,
        never an overwrite (events reference versions as evidence).
        """
        if self._config.model_version_id(version) is not None:
            raise DuplicateResourceError(
                f"model version '{version}' is already registered",
                field="version",
            )
        row = self._config.insert_model_version(
            {
                "version": version,
                "artefact_hash": artefact_hash,
                "classes": classes,
                "training_data_hash": training_data_hash,
                "model_card_ref": model_card_ref,
                "datasheet_ref": datasheet_ref,
                "notes": notes,
            }
        )
        self._audit.write(
            action="model.registered",
            entity_type="model_version",
            actor_user_id=principal.user_id,
            entity_id=row.id,
            after_state={
                "version": version,
                "artefact_hash": artefact_hash,
                "classes": classes,
                "model_card_ref": model_card_ref,
                "datasheet_ref": datasheet_ref,
            },
            ip_address=ip_address,
        )
        self._session.commit()
        return row

    def list_model_versions(self, principal: HumanPrincipal) -> list[sa.Row]:
        del principal  # role-gated at the route; versions are tenant-global
        return list(self._config.list_model_versions())

    def approve_model_version(
        self, principal: HumanPrincipal, model_version_id: UUID, ip_address: str | None
    ) -> sa.Row:
        """Record the named G1 approver — GOVERNANCE.md 9.

        Approval requires the model card AND datasheet references to exist:
        an approval with nothing to have reviewed is not evidence. The
        approver comes from the token; there is no parameter for it
        (the BR-C-02 pattern).
        """
        before = self._config.get_model_version(model_version_id)
        if before is None:
            raise NotFoundError("model version not found")
        if before.approved_by is not None:
            raise DuplicateResourceError("model version is already approved")
        if before.model_card_ref is None or before.datasheet_ref is None:
            raise ValidationFailureError(
                "approval requires a model card and a dataset datasheet "
                "reference (gate G1, GOVERNANCE.md 9)",
                field="model_card_ref",
            )
        approved_at = datetime.now(timezone.utc)
        row = self._config.update_model_version(
            model_version_id,
            {"approved_by": principal.user_id, "approved_at": approved_at},
        )
        self._audit.write(
            action="model.approved",
            entity_type="model_version",
            actor_user_id=principal.user_id,
            entity_id=model_version_id,
            before_state={"approved_by": None},
            after_state={
                "approved_by": str(principal.user_id),
                "approved_at": approved_at.isoformat(),
            },
            ip_address=ip_address,
        )
        self._session.commit()
        return row  # type: ignore[return-value]

    # -- agent config pull (IF-X1) -------------------------------------------

    def agent_config(self, site_id: UUID) -> dict[str, Any]:
        document = self._config.agent_config_document(site_id)
        if document is None:
            raise NotFoundError("site not found")
        return document

    # -- internal ------------------------------------------------------------

    @staticmethod
    def _ensure_site_scope(principal: HumanPrincipal, site_id: UUID) -> None:
        """Config mutations require the acting role AT THIS SITE. The role
        itself is asserted by the route dependency; this pins it to the
        site (TRD 12.3 — roles are site-scoped)."""
        if site_id not in principal.site_ids():
            raise ScopeError("site is outside your scope")
