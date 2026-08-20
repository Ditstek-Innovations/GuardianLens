"""MOD-10 — configuration CRUD, attribution, audit atomicity, agent pull."""

from __future__ import annotations

import uuid

import pytest

from guardian_lens.services.audit import AuditService
from tests.api.conftest import bearer

STREAM_URL = "rtsp://user:secret-cam-password@192.168.1.10/stream2"


def _create_camera(client, api_seed, admin_token, **overrides):
    body = {
        "site_id": str(api_seed["site_a"]),
        "name": f"cam-{uuid.uuid4().hex[:8]}",
        "stream_url": STREAM_URL,
        **overrides,
    }
    return client.post(
        "/api/v1/cameras", json=body, headers=bearer(admin_token)
    )


def test_site_create_and_list(client, admin_token):
    response = client.post(
        "/api/v1/sites",
        json={"name": "New Wing", "timezone": "Asia/Kolkata"},
        headers=bearer(admin_token),
    )
    assert response.status_code == 201
    site_id = response.json()["id"]
    # The creator was granted site_admin at the new site in the same
    # transaction, so the site is visible and manageable immediately —
    # but only with a FRESH token carrying the new grant.
    listed = client.get("/api/v1/sites", headers=bearer(admin_token))
    assert listed.status_code == 200
    assert site_id not in [s["id"] for s in listed.json()]  # old token, old scope


def test_reviewer_cannot_create_camera(client, api_seed, reviewer_token):
    response = _create_camera(client, api_seed, reviewer_token)
    assert response.status_code == 403


@pytest.mark.proposed_rule("BR-S-03")
def test_camera_response_and_storage_never_contain_stream_url(
    client, api_seed, admin_token, tenant_conn
):
    response = _create_camera(client, api_seed, admin_token)
    assert response.status_code == 201, response.text
    body = response.json()
    assert "stream_url" not in body
    assert "stream_url_encrypted" not in body
    assert STREAM_URL not in response.text

    stored = tenant_conn.execute(
        "SELECT stream_url_encrypted FROM cameras WHERE id = %s", (body["id"],)
    ).fetchone()[0]
    # Sealed, never plaintext: neither the URL nor the password appears in
    # the stored bytes (BR-S-03).
    assert STREAM_URL.encode() not in bytes(stored)
    assert b"secret-cam-password" not in bytes(stored)


def test_camera_create_rejects_rtsp_url_without_host(
    client, api_seed, admin_token
):
    """rtsp:192.168.0.20 (missing //) cannot be opened by FFmpeg."""
    response = _create_camera(
        client, api_seed, admin_token, stream_url="rtsp:10.11.12.13"
    )
    assert response.status_code == 422
    assert response.json()["error"]["field"] == "stream_url"
    assert "10.11.12.13" not in response.text


@pytest.mark.active_rule("BR-010")
def test_camera_audit_entry_never_contains_credential(
    client, api_seed, admin_token, tenant_conn
):
    response = _create_camera(client, api_seed, admin_token)
    camera_id = response.json()["id"]
    audit = tenant_conn.execute(
        "SELECT after_state::text FROM audit_log"
        " WHERE entity_type = 'camera' AND entity_id = %s",
        (camera_id,),
    ).fetchall()
    assert audit, "camera.created must be audited"
    for (state,) in audit:
        assert "secret-cam-password" not in state
        assert "stream_url_encrypted" not in state


@pytest.mark.active_rule("BR-001")
def test_rule_is_created_inactive(client, api_seed, manager_token):
    response = client.post(
        "/api/v1/rules",
        json={
            "zone_id": str(api_seed["zone_a"]),
            "rule_type": "ppe_vest",
            "confidence_threshold": 0.6,
            "debounce_seconds": 30,
            "human_readable": "Vest required in Bay 3",
        },
        headers=bearer(manager_token),
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["is_active"] is False
    assert body["activated_by"] is None


@pytest.mark.active_rule("BR-001")
def test_rule_create_cannot_smuggle_is_active(client, api_seed, manager_token):
    """extra="forbid": is_active is not a creation field at all."""
    response = client.post(
        "/api/v1/rules",
        json={
            "zone_id": str(api_seed["zone_a"]),
            "rule_type": "ppe_vest",
            "confidence_threshold": 0.6,
            "debounce_seconds": 30,
            "human_readable": "Vest required",
            "is_active": True,
        },
        headers=bearer(manager_token),
    )
    assert response.status_code == 422


@pytest.mark.proposed_rule("BR-C-02")
def test_activation_sets_named_activator(
    client, api_seed, manager_token, tenant_conn
):
    created = client.post(
        "/api/v1/rules",
        json={
            "zone_id": str(api_seed["zone_a"]),
            "rule_type": "zone_intrusion",
            "confidence_threshold": 0.7,
            "debounce_seconds": 60,
            "human_readable": "No entry while press is live",
        },
        headers=bearer(manager_token),
    ).json()

    activated = client.post(
        f"/api/v1/rules/{created['id']}/activate", headers=bearer(manager_token)
    )
    assert activated.status_code == 200
    body = activated.json()
    assert body["is_active"] is True
    assert body["activated_by"] == str(api_seed["manager_a"])
    assert body["activated_at"] is not None

    audit = tenant_conn.execute(
        "SELECT count(*) FROM audit_log WHERE entity_type = 'rule'"
        " AND entity_id = %s AND action = 'rule.activated'",
        (created["id"],),
    ).fetchone()[0]
    assert audit == 1


@pytest.mark.proposed_rule("BR-C-02")
def test_patch_is_active_true_routes_through_activation(
    client, api_seed, manager_token
):
    created = client.post(
        "/api/v1/rules",
        json={
            "zone_id": str(api_seed["zone_a"]),
            "rule_type": "ppe_gloves",
            "confidence_threshold": 0.5,
            "debounce_seconds": 30,
            "human_readable": "Gloves required",
        },
        headers=bearer(manager_token),
    ).json()
    patched = client.patch(
        f"/api/v1/rules/{created['id']}",
        json={"is_active": True},
        headers=bearer(manager_token),
    )
    assert patched.status_code == 200
    assert patched.json()["activated_by"] == str(api_seed["manager_a"])


@pytest.mark.proposed_rule("BR-C-01")
def test_config_mutation_rolls_back_when_audit_fails(
    client, api_seed, manager_token, tenant_conn, monkeypatch
):
    """A configuration change that cannot be audited must not take effect."""
    zone_name = f"doomed-zone-{uuid.uuid4().hex[:8]}"

    def refuse(self, **kwargs):  # noqa: ANN001, ANN003
        raise RuntimeError("audit store unavailable (injected)")

    monkeypatch.setattr(AuditService, "write", refuse)
    response = client.post(
        "/api/v1/zones",
        json={
            "camera_id": str(api_seed["camera_a"]),
            "name": zone_name,
            "polygon": [[0.1, 0.1], [0.9, 0.1], [0.5, 0.9]],
        },
        headers=bearer(manager_token),
    )
    assert response.status_code == 500
    monkeypatch.undo()

    count = tenant_conn.execute(
        "SELECT count(*) FROM zones WHERE name = %s", (zone_name,)
    ).fetchone()[0]
    assert count == 0


def test_zone_crud_with_audit(client, api_seed, manager_token, tenant_conn):
    created = client.post(
        "/api/v1/zones",
        json={
            "camera_id": str(api_seed["camera_a"]),
            "name": "loading dock",
            "polygon": [[0.0, 0.0], [1.0, 0.0], [1.0, 1.0]],
        },
        headers=bearer(manager_token),
    )
    assert created.status_code == 201
    zone_id = created.json()["id"]

    patched = client.patch(
        f"/api/v1/zones/{zone_id}",
        json={"name": "loading dock north"},
        headers=bearer(manager_token),
    )
    assert patched.status_code == 200
    assert patched.json()["name"] == "loading dock north"

    deleted = client.delete(
        f"/api/v1/zones/{zone_id}", headers=bearer(manager_token)
    )
    assert deleted.status_code == 204

    actions = [
        row[0]
        for row in tenant_conn.execute(
            "SELECT action FROM audit_log WHERE entity_type = 'zone'"
            " AND entity_id = %s ORDER BY id",
            (zone_id,),
        ).fetchall()
    ]
    assert actions == ["zone.created", "zone.updated", "zone.deleted"]


def test_agent_config_pull_and_304(client, api_seed, agent_token, manager_token):
    agent_id = api_seed["agent_a"]
    first = client.get(
        f"/api/v1/agents/{agent_id}/config", headers=bearer(agent_token)
    )
    assert first.status_code == 200
    document = first.json()
    etag = first.headers["etag"]

    # Only site A, only ACTIVE rules, credentials sealed.
    assert document["site"]["id"] == str(api_seed["site_a"])
    assert all(r["id"] != str(api_seed["rule_b"]) for r in document["rules"])
    assert all("stream_url" not in c for c in document["cameras"])
    assert all(c["stream_url_sealed"] for c in document["cameras"])

    unchanged = client.get(
        f"/api/v1/agents/{agent_id}/config",
        headers={**bearer(agent_token), "If-None-Match": etag},
    )
    assert unchanged.status_code == 304

    # A config mutation bumps the version; the same If-None-Match now misses.
    client.post(
        "/api/v1/zones",
        json={
            "camera_id": str(api_seed["camera_a"]),
            "name": f"zone-{uuid.uuid4().hex[:6]}",
            "polygon": [[0.2, 0.2], [0.8, 0.2], [0.5, 0.8]],
        },
        headers=bearer(manager_token),
    )
    changed = client.get(
        f"/api/v1/agents/{agent_id}/config",
        headers={**bearer(agent_token), "If-None-Match": etag},
    )
    assert changed.status_code == 200
    assert changed.headers["etag"] != etag


def test_agent_config_is_agent_only_and_self_only(
    client, api_seed, agent_token, admin_token
):
    agent_id = api_seed["agent_a"]
    human = client.get(
        f"/api/v1/agents/{agent_id}/config", headers=bearer(admin_token)
    )
    assert human.status_code == 403

    other = client.get(
        f"/api/v1/agents/{api_seed['agent_b']}/config",
        headers=bearer(agent_token),
    )
    assert other.status_code == 403


def test_manager_cannot_touch_cameras(client, api_seed, manager_token):
    """TRD 12.3: safety_manager config scope is zones and rules only."""
    response = _create_camera(client, api_seed, manager_token)
    assert response.status_code == 403


def test_audit_read_roles(client, admin_token, auditor_token, reviewer_token):
    for token, expected in (
        (auditor_token, 200),
        (admin_token, 200),
        (reviewer_token, 403),
    ):
        response = client.get("/api/v1/audit", headers=bearer(token))
        assert response.status_code == expected


@pytest.mark.active_rule("BR-AU-01")
def test_audit_route_has_no_delete_or_patch(client, admin_token):
    """TRD 10.9 — endpoints that must never exist."""
    assert client.delete("/api/v1/audit", headers=bearer(admin_token)).status_code in (404, 405)
    assert client.patch("/api/v1/audit", headers=bearer(admin_token)).status_code in (404, 405)
