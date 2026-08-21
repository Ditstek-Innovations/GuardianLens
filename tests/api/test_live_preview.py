"""Authenticated edge preview publication and scoped human reads."""

from __future__ import annotations

from datetime import datetime, timezone

from tests.api.conftest import FRAME_BYTES, bearer


def test_agent_preview_is_visible_to_scoped_reviewer(
    client, api_seed, agent_token, reviewer_token
):
    captured_at = datetime.now(timezone.utc).isoformat()
    published = client.post(
        f"/api/v1/agents/cameras/{api_seed['camera_a']}/preview",
        content=FRAME_BYTES,
        headers={
            **bearer(agent_token),
            "Content-Type": "image/jpeg",
            "X-Captured-At": captured_at,
        },
    )
    assert published.status_code == 204, published.text

    preview = client.get(
        f"/api/v1/cameras/{api_seed['camera_a']}/live-frame",
        headers=bearer(reviewer_token),
    )
    assert preview.status_code == 200
    assert preview.content == FRAME_BYTES
    assert preview.headers["content-type"].startswith("image/jpeg")
    assert preview.headers["cache-control"] == "private, no-store"
    assert preview.headers["x-captured-at"]


def test_preview_routes_enforce_principal_type_and_site_scope(
    client, api_seed, agent_token, reviewer_token
):
    headers = {
        **bearer(agent_token),
        "Content-Type": "image/jpeg",
        "X-Captured-At": datetime.now(timezone.utc).isoformat(),
    }
    wrong_site = client.post(
        f"/api/v1/agents/cameras/{api_seed['camera_b']}/preview",
        content=FRAME_BYTES,
        headers=headers,
    )
    assert wrong_site.status_code == 404

    reviewer_cross_site = client.get(
        f"/api/v1/cameras/{api_seed['camera_b']}/live-frame",
        headers=bearer(reviewer_token),
    )
    assert reviewer_cross_site.status_code == 404

    human_publish = client.post(
        f"/api/v1/agents/cameras/{api_seed['camera_a']}/preview",
        content=FRAME_BYTES,
        headers={
            **bearer(reviewer_token),
            "Content-Type": "image/jpeg",
            "X-Captured-At": datetime.now(timezone.utc).isoformat(),
        },
    )
    assert human_publish.status_code == 403


def test_preview_rejects_non_jpeg_payload(client, api_seed, agent_token):
    response = client.post(
        f"/api/v1/agents/cameras/{api_seed['camera_a']}/preview",
        content=b"not-a-jpeg",
        headers={
            **bearer(agent_token),
            "Content-Type": "image/jpeg",
            "X-Captured-At": datetime.now(timezone.utc).isoformat(),
        },
    )
    assert response.status_code == 400


def test_admin_can_queue_ptz_command_for_scoped_edge(
    client, api_seed, admin_token, reviewer_token, agent_token
):
    queued = client.post(
        f"/api/v1/cameras/{api_seed['camera_a']}/ptz",
        json={"direction": "left"},
        headers=bearer(admin_token),
    )
    assert queued.status_code == 202, queued.text
    assert queued.json()["direction"] == "left"

    forbidden = client.post(
        f"/api/v1/cameras/{api_seed['camera_a']}/ptz",
        json={"direction": "right"},
        headers=bearer(reviewer_token),
    )
    assert forbidden.status_code == 403

    commands = client.get(
        "/api/v1/agents/ptz-commands", headers=bearer(agent_token)
    )
    assert commands.status_code == 200
    assert commands.json()[0]["camera_id"] == str(api_seed["camera_a"])
    assert commands.json()[0]["direction"] == "left"

    delivered_once = client.get(
        "/api/v1/agents/ptz-commands", headers=bearer(agent_token)
    )
    assert delivered_once.json() == []
