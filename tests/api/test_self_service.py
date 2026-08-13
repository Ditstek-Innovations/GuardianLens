"""CS-AU-10 (v1.4) — self-service sign-up and password reset.

The enumeration assertions compare raw response BYTES, not parsed shapes:
"no response ever distinguishes a known address from an unknown one" is a
property of the octets on the wire, and a byte-for-byte comparison is the
strictest executable form of it.
"""

from __future__ import annotations

import logging
import uuid

from tests.api.conftest import bearer

VALID_PASSWORD = "a-long-enough-passphrase-1"
NEW_PASSWORD = "an-entirely-new-passphrase-2"

SIGNUP_URL = "/api/v1/auth/signup"
RESET_REQUEST_URL = "/api/v1/auth/password-reset-request"
RESET_URL = "/api/v1/auth/password-reset"

DELIVERY_LOGGER = "guardian_lens.reset_delivery"


def _fresh_email(tag: str) -> str:
    return f"selfsvc-{tag}-{uuid.uuid4().hex[:8]}@example.test"


def _signup(client, site_code: str, email: str, password: str = VALID_PASSWORD):
    return client.post(
        SIGNUP_URL,
        json={
            "full_name": "Self Service",
            "email": email,
            "password": password,
            "site_code": site_code,
        },
    )


def _login(client, email: str, password: str):
    return client.post(
        "/api/v1/auth/login", json={"email": email, "password": password}
    )


def _user_id(tenant_conn, email: str) -> uuid.UUID:
    row = tenant_conn.execute(
        "SELECT id FROM users WHERE email = %s", (email,)
    ).fetchone()
    assert row is not None, f"no user row for {email}"
    return row[0]


def _request_reset_token(client, caplog, email: str) -> str:
    """Drive the reset-request flow and capture the token from the dev
    delivery channel — the log line standing in for the reset email."""
    with caplog.at_level(logging.INFO, logger=DELIVERY_LOGGER):
        response = client.post(RESET_REQUEST_URL, json={"email": email})
    assert response.status_code == 202, response.text
    for record in reversed(caplog.records):
        message = record.getMessage()
        if record.name == DELIVERY_LOGGER and email in message:
            return message.rsplit(": ", 1)[1]
    raise AssertionError("no delivery log line carried the reset token")


# -- sign-up ------------------------------------------------------------------


def test_signup_creates_user_directory_entry_and_audit(
    client, tenant_slug, tenant_conn, control_db
):
    from guardian_lens.tenancy.registry import email_hash

    email = _fresh_email("created")
    response = _signup(client, tenant_slug, email)
    assert response.status_code == 202
    assert response.json() == {
        "status": "accepted",
        "message": "Account requested. A site administrator assigns access.",
    }

    # The tenant user: active, argon2-hashed, and NEVER the password.
    row = tenant_conn.execute(
        "SELECT id, is_active, password_hash FROM users WHERE email = %s",
        (email,),
    ).fetchone()
    assert row is not None
    user_id, is_active, password_hash = row
    assert is_active is True
    assert password_hash.startswith("$argon2")
    assert VALID_PASSWORD not in password_hash

    # The control-plane directory routes the address to this tenant —
    # hash only, same discipline as bootstrap.
    directory = control_db.execute(
        "SELECT t.slug FROM user_directory d"
        " JOIN tenants t ON t.id = d.tenant_id WHERE d.email_hash = %s",
        (email_hash(email),),
    ).fetchone()
    assert directory is not None and directory[0] == tenant_slug

    # The audit entry: actor-less under the system.* prefix rule, user id
    # in entity_id, and no credential material in the state.
    audit = tenant_conn.execute(
        "SELECT actor_user_id, actor_agent_id, after_state FROM audit_log"
        " WHERE action = 'system.user.signed_up' AND entity_id = %s",
        (user_id,),
    ).fetchone()
    assert audit is not None
    actor_user_id, actor_agent_id, after_state = audit
    assert actor_user_id is None and actor_agent_id is None
    assert after_state == {
        "email": email,
        "full_name": "Self Service",
        "is_active": True,
    }


def test_signup_acceptance_is_byte_identical_across_all_outcomes(
    client, app, monkeypatch, tenant_slug, tenant_conn
):
    """CS-AU-16 — creation, duplicate address, unknown site code and a
    disabled deployment answer with the SAME bytes. This is the
    enumeration test: if any branch leaked, these would differ."""
    email = _fresh_email("enum")

    created = _signup(client, tenant_slug, email)

    app.state.signup_limiter.reset()
    duplicate = _signup(client, tenant_slug, email)

    app.state.signup_limiter.reset()
    unknown_site = _signup(client, "no_such_site_code", _fresh_email("enum"))

    app.state.signup_limiter.reset()
    monkeypatch.setattr(app.state.settings, "signup_enabled", False)
    disabled = _signup(client, tenant_slug, _fresh_email("enum"))

    for response in (created, duplicate, unknown_site, disabled):
        assert response.status_code == 202
        assert response.content == created.content

    # And only the first attempt created anything.
    count = tenant_conn.execute(
        "SELECT count(*) FROM users WHERE email = %s", (email,)
    ).fetchone()[0]
    assert count == 1


def test_signed_up_user_can_log_in_but_holds_no_access(client, tenant_slug):
    """CS-AU-10 — signing up grants an identity, never access: login works,
    the token carries no roles, and every route is 403."""
    email = _fresh_email("grantless")
    assert _signup(client, tenant_slug, email).status_code == 202

    login = _login(client, email, VALID_PASSWORD)
    assert login.status_code == 200, login.text
    assert login.json()["user"]["roles"] == []

    events = client.get(
        "/api/v1/events", headers=bearer(login.json()["access_token"])
    )
    assert events.status_code == 403


def test_signup_password_below_minimum_is_a_422_field_error(
    client, tenant_slug
):
    """CS-AU-15 — 12..128, no composition rules. Password quality is about
    the caller's own submission; it is not enumeration-sensitive."""
    short = _signup(client, tenant_slug, _fresh_email("short"), "elevenchars")
    assert short.status_code == 422
    assert short.json()["error"]["code"] == "GL-4220"
    assert short.json()["error"]["field"] == "password"

    over_maximum = _signup(client, tenant_slug, _fresh_email("long"), "x" * 129)
    assert over_maximum.status_code == 422
    assert over_maximum.json()["error"]["field"] == "password"


def test_signup_rate_limit(client, tenant_slug):
    """3/min/IP on sign-up, through the same limiter mechanism as login."""
    for _ in range(3):
        assert _signup(client, tenant_slug, _fresh_email("rate")).status_code == 202
    fourth = _signup(client, tenant_slug, _fresh_email("rate"))
    assert fourth.status_code == 429
    assert fourth.json()["error"]["code"] == "GL-4290"


# -- password reset request ---------------------------------------------------


def test_reset_request_is_byte_identical_for_known_and_unknown(
    client, api_seed
):
    """CS-AU-17 — 'if that address has an account...' holds because the
    known-address response IS the unknown-address response."""
    known = client.post(
        RESET_REQUEST_URL, json={"email": api_seed["emails"]["reviewer_a"]}
    )
    unknown = client.post(
        RESET_REQUEST_URL, json={"email": "nobody@example.test"}
    )
    assert known.status_code == unknown.status_code == 202
    assert known.content == unknown.content
    assert known.json() == {"status": "accepted"}


def test_reset_request_supersedes_prior_tokens(
    client, caplog, tenant_slug, tenant_conn
):
    """A fresh request leaves exactly one live token: every prior unused
    token is stamped used, and only hashes are ever stored."""
    email = _fresh_email("supersede")
    assert _signup(client, tenant_slug, email).status_code == 202

    first = _request_reset_token(client, caplog, email)
    second = _request_reset_token(client, caplog, email)
    assert first != second

    user_id = _user_id(tenant_conn, email)
    live, total = tenant_conn.execute(
        "SELECT count(*) FILTER (WHERE used_at IS NULL), count(*)"
        " FROM password_reset_tokens WHERE user_id = %s",
        (user_id,),
    ).fetchone()
    assert (live, total) == (1, 2)

    # Stored form is sha256, never the token (TRD 12.4 discipline).
    for (token_hash,) in tenant_conn.execute(
        "SELECT token_hash FROM password_reset_tokens WHERE user_id = %s",
        (user_id,),
    ).fetchall():
        assert len(bytes(token_hash)) == 32
        assert bytes(token_hash) not in (first.encode(), second.encode())


# -- password reset -----------------------------------------------------------


def test_full_reset_flow_rotates_credential_and_kills_sessions(
    client, caplog, tenant_slug
):
    """Request -> token from the delivery channel -> reset: the old
    password stops working, the new one works, and a refresh token issued
    BEFORE the reset is dead after it (every session revoked)."""
    email = _fresh_email("flow")
    assert _signup(client, tenant_slug, email).status_code == 202

    before = _login(client, email, VALID_PASSWORD)
    assert before.status_code == 200
    old_refresh = before.json()["refresh_token"]

    token = _request_reset_token(client, caplog, email)
    reset = client.post(
        RESET_URL,
        json={"email": email, "token": token, "new_password": NEW_PASSWORD},
    )
    assert reset.status_code == 200, reset.text
    assert reset.json() == {"status": "ok"}

    assert _login(client, email, VALID_PASSWORD).status_code == 401
    assert _login(client, email, NEW_PASSWORD).status_code == 200

    refreshed = client.post(
        "/api/v1/auth/refresh", json={"refresh_token": old_refresh}
    )
    assert refreshed.status_code == 401


def _assert_generic_reset_failure(response) -> None:
    """The ONE failure the reset route may produce (CS-AU-17): never a
    hint about why the token failed."""
    assert response.status_code == 400
    error = response.json()["error"]
    assert error["code"] == "GL-4003"
    assert error["message"] == "The reset link is invalid or has expired."


def test_expired_reset_token_is_rejected_generically(
    client, caplog, tenant_slug, tenant_conn
):
    email = _fresh_email("expired")
    assert _signup(client, tenant_slug, email).status_code == 202
    token = _request_reset_token(client, caplog, email)

    # Age the token past its window. chk_reset_expiry_ordered still holds:
    # one millisecond after creation is ordered, and long past.
    tenant_conn.execute(
        "UPDATE password_reset_tokens"
        " SET expires_at = created_at + interval '1 millisecond'"
        " WHERE user_id = %s",
        (_user_id(tenant_conn, email),),
    )
    tenant_conn.commit()

    _assert_generic_reset_failure(
        client.post(
            RESET_URL,
            json={"email": email, "token": token, "new_password": NEW_PASSWORD},
        )
    )
    # And the credential did not move.
    assert _login(client, email, VALID_PASSWORD).status_code == 200


def test_reset_token_is_single_use(client, caplog, tenant_slug):
    email = _fresh_email("reuse")
    assert _signup(client, tenant_slug, email).status_code == 202
    token = _request_reset_token(client, caplog, email)

    first = client.post(
        RESET_URL,
        json={"email": email, "token": token, "new_password": NEW_PASSWORD},
    )
    assert first.status_code == 200

    _assert_generic_reset_failure(
        client.post(
            RESET_URL,
            json={
                "email": email,
                "token": token,
                "new_password": "yet-another-passphrase-3",
            },
        )
    )
    # The replay changed nothing: the first reset's credential stands.
    assert _login(client, email, NEW_PASSWORD).status_code == 200


def test_reset_token_bound_to_wrong_email_is_rejected(
    client, caplog, tenant_slug
):
    """A valid token presented with a different account's address is the
    same generic failure — a token is a capability for ONE user."""
    email_a = _fresh_email("owner")
    email_b = _fresh_email("other")
    assert _signup(client, tenant_slug, email_a).status_code == 202
    assert _signup(client, tenant_slug, email_b).status_code == 202
    token_a = _request_reset_token(client, caplog, email_a)

    _assert_generic_reset_failure(
        client.post(
            RESET_URL,
            json={
                "email": email_b,
                "token": token_a,
                "new_password": NEW_PASSWORD,
            },
        )
    )
    # The mismatch consumed nothing: the owner's token still redeems.
    owner = client.post(
        RESET_URL,
        json={"email": email_a, "token": token_a, "new_password": NEW_PASSWORD},
    )
    assert owner.status_code == 200


def test_reset_policy_violation_is_a_422_on_new_password(
    client, caplog, tenant_slug
):
    """The one non-generic reset failure: password policy, which speaks
    about the caller's own submission, not about the token (CS-AU-15)."""
    email = _fresh_email("policy")
    assert _signup(client, tenant_slug, email).status_code == 202
    token = _request_reset_token(client, caplog, email)

    response = client.post(
        RESET_URL,
        json={"email": email, "token": token, "new_password": "elevenchars"},
    )
    assert response.status_code == 422
    assert response.json()["error"]["field"] == "new_password"
    # And the policy failure did not spend the token.
    ok = client.post(
        RESET_URL,
        json={"email": email, "token": token, "new_password": NEW_PASSWORD},
    )
    assert ok.status_code == 200


def test_reset_endpoints_rate_limit(client):
    """3/min/IP on reset-request, 5/min/IP on reset."""
    for _ in range(3):
        assert (
            client.post(
                RESET_REQUEST_URL, json={"email": "nobody@example.test"}
            ).status_code
            == 202
        )
    fourth = client.post(RESET_REQUEST_URL, json={"email": "nobody@example.test"})
    assert fourth.status_code == 429

    for _ in range(5):
        response = client.post(
            RESET_URL,
            json={
                "email": "nobody@example.test",
                "token": "not-a-token",
                "new_password": NEW_PASSWORD,
            },
        )
        assert response.status_code == 400
    sixth = client.post(
        RESET_URL,
        json={
            "email": "nobody@example.test",
            "token": "not-a-token",
            "new_password": NEW_PASSWORD,
        },
    )
    assert sixth.status_code == 429
    assert sixth.json()["error"]["code"] == "GL-4290"
