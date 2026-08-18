"""Agent-principal and model-version registration — WORKFLOW.md 7 gap 1.

The credential contract under test: registration returns the composite
``slug:agent_id:secret`` exactly once, the stored form is an Argon2 hash,
and the composite works against the real /auth/agent exchange. Model
versions carry the gate-G1 evidence trail: registration records card and
datasheet references, approval requires them and names the approver from
the token (GOVERNANCE.md 9).
"""

from __future__ import annotations

import uuid
from typing import Any

from fastapi.testclient import TestClient

from tests.api.conftest import bearer


def _register_agent(
    client: TestClient, token: str, api_seed: dict[str, Any], name: str
) -> dict[str, Any]:
    response = client.post(
        "/api/v1/agents",
        json={"site_id": str(api_seed["site_a"]), "name": name},
        headers=bearer(token),
    )
    assert response.status_code == 201, response.text
    return response.json()


class TestAgentRegistration:
    def test_returns_one_time_credential_that_exchanges_for_a_token(
        self,
        client: TestClient,
        admin_token: str,
        api_seed: dict[str, Any],
        tenant_slug: str,
    ) -> None:
        body = _register_agent(client, admin_token, api_seed, "edge-box-01")

        slug, agent_id, secret = body["credential"].split(":", 2)
        assert slug == tenant_slug
        assert agent_id == body["id"]
        assert len(secret) >= 32
        # No credential material beyond the one-time composite.
        assert "credential_hash" not in body
        assert body["status"] == "offline"

        exchange = client.post(
            "/api/v1/auth/agent", json={"credential": body["credential"]}
        )
        assert exchange.status_code == 200, exchange.text
        assert exchange.json()["access_token"]

    def test_listing_shows_the_agent_without_credential_material(
        self, client: TestClient, admin_token: str, api_seed: dict[str, Any]
    ) -> None:
        created = _register_agent(client, admin_token, api_seed, "edge-box-02")
        response = client.get("/api/v1/agents", headers=bearer(admin_token))
        assert response.status_code == 200
        rows = {row["id"]: row for row in response.json()}
        assert created["id"] in rows
        listed = rows[created["id"]]
        assert "credential" not in listed
        assert "credential_hash" not in listed

    def test_requires_site_admin(
        self,
        client: TestClient,
        manager_token: str,
        reviewer_token: str,
        api_seed: dict[str, Any],
    ) -> None:
        payload = {"site_id": str(api_seed["site_a"]), "name": "edge-box-nope"}
        for token in (manager_token, reviewer_token):
            response = client.post(
                "/api/v1/agents", json=payload, headers=bearer(token)
            )
            assert response.status_code == 403, response.text
            assert response.json()["error"]["code"].startswith("GL-403")

    def test_registration_is_audited(
        self,
        client: TestClient,
        admin_token: str,
        api_seed: dict[str, Any],
        tenant_conn,
    ) -> None:
        created = _register_agent(client, admin_token, api_seed, "edge-box-03")
        row = tenant_conn.execute(
            "SELECT action, after_state FROM audit_log"
            " WHERE entity_id = %s AND action = 'agent.registered'",
            (created["id"],),
        ).fetchone()
        assert row is not None
        assert row[1]["name"] == "edge-box-03"
        assert "credential_hash" not in row[1]


class TestModelVersions:
    def test_register_list_and_duplicate_conflict(
        self, client: TestClient, admin_token: str
    ) -> None:
        version = f"2.0.0-{uuid.uuid4().hex[:8]}"
        payload = {
            "version": version,
            "artefact_hash": "sha256:abc123",
            "classes": ["person_without_helmet"],
        }
        created = client.post(
            "/api/v1/model-versions", json=payload, headers=bearer(admin_token)
        )
        assert created.status_code == 201, created.text
        assert created.json()["approved_by"] is None
        assert created.json()["deployed_at"] is None

        listed = client.get("/api/v1/model-versions", headers=bearer(admin_token))
        assert version in [row["version"] for row in listed.json()]

        duplicate = client.post(
            "/api/v1/model-versions", json=payload, headers=bearer(admin_token)
        )
        assert duplicate.status_code == 409, duplicate.text
        assert duplicate.json()["error"]["code"] == "GL-4092"

    def test_approval_requires_g1_evidence_references(
        self, client: TestClient, admin_token: str, api_seed: dict[str, Any]
    ) -> None:
        bare = client.post(
            "/api/v1/model-versions",
            json={
                "version": f"2.1.0-{uuid.uuid4().hex[:8]}",
                "artefact_hash": "sha256:def456",
                "classes": ["person_without_helmet"],
            },
            headers=bearer(admin_token),
        ).json()
        refused = client.post(
            f"/api/v1/model-versions/{bare['id']}/approve",
            headers=bearer(admin_token),
        )
        assert refused.status_code == 422, refused.text

        evidenced = client.post(
            "/api/v1/model-versions",
            json={
                "version": f"2.2.0-{uuid.uuid4().hex[:8]}",
                "artefact_hash": "sha256:ghi789",
                "classes": ["person_without_helmet"],
                "model_card_ref": "docs/models/helmet-2.2.0-card.md",
                "datasheet_ref": "docs/datasets/site-frames-2026Q2.md",
            },
            headers=bearer(admin_token),
        ).json()
        approved = client.post(
            f"/api/v1/model-versions/{evidenced['id']}/approve",
            headers=bearer(admin_token),
        )
        assert approved.status_code == 200, approved.text
        assert approved.json()["approved_by"] == str(api_seed["admin"])
        assert approved.json()["approved_at"] is not None

        again = client.post(
            f"/api/v1/model-versions/{evidenced['id']}/approve",
            headers=bearer(admin_token),
        )
        assert again.status_code == 409, again.text

    def test_requires_site_admin(
        self, client: TestClient, manager_token: str
    ) -> None:
        response = client.post(
            "/api/v1/model-versions",
            json={
                "version": "9.9.9",
                "artefact_hash": "sha256:zzz",
                "classes": ["person_without_helmet"],
            },
            headers=bearer(manager_token),
        )
        assert response.status_code == 403, response.text
