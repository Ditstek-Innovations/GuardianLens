"""Camera discovery import behavior."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from tests.api.conftest import bearer


def _auth_required_candidate(tenant_conn, site_id, ip_address):
    scan_id = uuid.uuid4()
    candidate_id = uuid.uuid4()
    now = datetime.now(timezone.utc)
    tenant_conn.execute(
        "INSERT INTO camera_discovery_scans "
        "(id, site_id, started_at, completed_at, scan_method, status, cameras_found) "
        "VALUES (%s, %s, %s, %s, 'rtsp_probe', 'completed', 1)",
        (scan_id, site_id, now, now),
    )
    tenant_conn.execute(
        "INSERT INTO camera_discovery_candidates "
        "(id, scan_id, site_id, discovered_at, ip_address, port, rtsp_paths, "
        "default_rtsp_path, resolution, codec, status, verified_at, created_at, updated_at) "
        "VALUES (%s, %s, %s, %s, %s, 554, %s, 'stream1', "
        "'Unknown (Auth Required)', 'Unknown', 'verified', %s, %s, %s)",
        (candidate_id, scan_id, site_id, now, ip_address, ["stream1"], now, now, now),
    )
    tenant_conn.commit()
    return candidate_id


def test_auth_required_candidate_can_be_imported_without_login(
    client, api_seed, admin_token, tenant_conn
):
    candidate_id = _auth_required_candidate(
        tenant_conn, api_seed["site_a"], "10.99.0.91"
    )

    response = client.post(
        f"/api/v1/discovery/candidates/{candidate_id}/adopt",
        headers=bearer(admin_token),
        json={
            "candidate_id": str(candidate_id),
            "name": "Login pending camera",
            "stream_profile": "secondary",
            "sample_rate_fps": 2,
            "rtsp_path": "stream1",
        },
    )

    assert response.status_code == 201, response.text
    imported = tenant_conn.execute(
        "SELECT imported_at, imported_camera_id FROM camera_discovery_candidates "
        "WHERE id = %s",
        (candidate_id,),
    ).fetchone()
    assert imported[0] is not None
    assert imported[1] == uuid.UUID(response.json()["id"])


def test_bulk_import_includes_auth_required_candidate(
    client, api_seed, admin_token, tenant_conn
):
    candidate_id = _auth_required_candidate(
        tenant_conn, api_seed["site_a"], "10.99.0.92"
    )

    response = client.post(
        "/api/v1/discovery/candidates/adopt-pending",
        params={"site_id": str(api_seed["site_a"])},
        headers=bearer(admin_token),
    )

    assert response.status_code == 200, response.text
    assert response.json()["imported_count"] >= 1
    assert response.json()["skipped_auth_required"] == 0
    assert tenant_conn.execute(
        "SELECT imported_at FROM camera_discovery_candidates WHERE id = %s",
        (candidate_id,),
    ).fetchone()[0] is not None
