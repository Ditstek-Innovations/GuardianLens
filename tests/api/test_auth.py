"""MOD-12 — login, refresh rotation, reuse detection, rate limiting."""

from __future__ import annotations

import pytest

from tests.api.conftest import PASSWORD, WRONG_PASSWORD, bearer


def _shape(body: dict) -> dict:
    """The response with its per-request noise removed, for comparing that
    two failures are indistinguishable."""
    error = dict(body.get("error", {}))
    error.pop("trace_id", None)
    return {"error": error}


def test_login_returns_tokens_and_user(client, api_seed):
    response = client.post(
        "/api/v1/auth/login",
        json={"email": api_seed["emails"]["reviewer_a"], "password": PASSWORD},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["expires_in"] == 900  # 15 minutes — TRD 12.2
    assert body["access_token"] and body["refresh_token"]
    assert body["user"]["roles"] == ["reviewer"]


def test_unknown_email_and_wrong_password_are_indistinguishable(client, api_seed):
    """DATABASE.md 1.5 — no user enumeration: identical status, identical
    body shape and content for unknown-address vs wrong-password."""
    unknown = client.post(
        "/api/v1/auth/login",
        json={"email": "nobody@example.test", "password": PASSWORD},
    )
    wrong = client.post(
        "/api/v1/auth/login",
        json={
            "email": api_seed["emails"]["reviewer_a"],
            "password": WRONG_PASSWORD,
        },
    )
    assert unknown.status_code == wrong.status_code == 401
    assert _shape(unknown.json()) == _shape(wrong.json())


def test_login_rate_limit(client, app):
    """TRD 12.7 — 5/min/IP on login."""
    app.state.login_limiter.reset()
    for _ in range(5):
        response = client.post(
            "/api/v1/auth/login",
            json={"email": "nobody@example.test", "password": "x"},
        )
        assert response.status_code == 401
    sixth = client.post(
        "/api/v1/auth/login",
        json={"email": "nobody@example.test", "password": "x"},
    )
    assert sixth.status_code == 429
    assert sixth.json()["error"]["code"] == "GL-4290"


def test_refresh_rotates_and_detects_reuse(client, api_seed):
    """TRD 12.2 — each refresh revokes its predecessor; reuse of a revoked
    token invalidates the whole family."""
    login = client.post(
        "/api/v1/auth/login",
        json={"email": api_seed["emails"]["manager_a"], "password": PASSWORD},
    ).json()
    first_refresh = login["refresh_token"]

    rotated = client.post(
        "/api/v1/auth/refresh", json={"refresh_token": first_refresh}
    )
    assert rotated.status_code == 200
    second_refresh = rotated.json()["refresh_token"]
    assert second_refresh != first_refresh

    # Reuse of the rotated-away token: rejected, and the family dies.
    reuse = client.post(
        "/api/v1/auth/refresh", json={"refresh_token": first_refresh}
    )
    assert reuse.status_code == 401

    # The current token was collateral of the family revocation.
    after_reuse = client.post(
        "/api/v1/auth/refresh", json={"refresh_token": second_refresh}
    )
    assert after_reuse.status_code == 401


def test_logout_revokes_refresh(client, api_seed):
    login = client.post(
        "/api/v1/auth/login",
        json={"email": api_seed["emails"]["auditor_a"], "password": PASSWORD},
    ).json()
    assert (
        client.post(
            "/api/v1/auth/logout",
            json={"refresh_token": login["refresh_token"]},
        ).status_code
        == 204
    )
    refreshed = client.post(
        "/api/v1/auth/refresh", json={"refresh_token": login["refresh_token"]}
    )
    assert refreshed.status_code == 401


def test_garbage_bearer_token_is_401(client):
    response = client.get(
        "/api/v1/events", headers=bearer("not-a-real-token")
    )
    assert response.status_code == 401


def test_refresh_token_is_not_a_bearer_credential(client, api_seed):
    """A refresh token must not open API routes; only access tokens do."""
    login = client.post(
        "/api/v1/auth/login",
        json={"email": api_seed["emails"]["reviewer_a"], "password": PASSWORD},
    ).json()
    response = client.get(
        "/api/v1/events", headers=bearer(login["refresh_token"])
    )
    assert response.status_code == 401


@pytest.mark.proposed_rule("BR-S-02")
def test_agent_credential_exchange(client, api_seed, tenant_slug):
    response = client.post(
        "/api/v1/auth/agent",
        json={
            "credential": f"{tenant_slug}:{api_seed['agent_a']}:"
            "edge-agent-shared-secret-for-tests"
        },
    )
    assert response.status_code == 200
    assert response.json()["expires_in"] == 900  # short-lived — TRD 12.2


def test_agent_exchange_with_wrong_secret_is_generic_401(client, api_seed, tenant_slug):
    response = client.post(
        "/api/v1/auth/agent",
        json={"credential": f"{tenant_slug}:{api_seed['agent_a']}:wrong"},
    )
    assert response.status_code == 401


def test_agent_exchange_with_unknown_slug_is_generic_401(client, api_seed):
    response = client.post(
        "/api/v1/auth/agent",
        json={"credential": f"no_such_tenant:{api_seed['agent_a']}:whatever"},
    )
    assert response.status_code == 401
