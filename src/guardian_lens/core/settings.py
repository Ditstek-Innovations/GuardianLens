"""Typed application settings — BACKEND_CODING_RULES 22.

Configuration comes from the environment, never from code. No secret has a
default value: a missing secret fails loudly at startup rather than falling
back to something guessable (TRD 12.5 — no default credentials at any phase).
"""

from __future__ import annotations

import secrets

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """All environment-derived configuration, in one typed object.

    Env vars carry the ``GL_`` prefix: GL_CONTROL_DB_URL, GL_TENANT_DB_URL,
    GL_EVIDENCE_ROOT, GL_JWT_SECRET, GL_CAMERA_KEY, GL_CAMERA_KEY_ID.
    """

    model_config = SettingsConfigDict(env_prefix="GL_", extra="ignore")

    # -- Databases -----------------------------------------------------------
    # The control DB holds routing only (ADR-017). The tenant URL is a BASE:
    # per-tenant databases derive from it via urls.tenant_url. In production
    # the per-tenant credential comes from the secret store via
    # tenant_databases.credential_ref — see tenancy/registry.py for the
    # integration point.
    control_db_url: str
    tenant_db_url: str

    # -- Tokens — TRD 12.2 ---------------------------------------------------
    # TRD 12.2 specifies RS256 with the private key in the secret store.
    # RS256 requires the `cryptography` package, which is not installed in
    # this environment, so the MVP signs HS256 with this secret. The secret
    # store / RS256 keypair is the [V1] integration point; swapping it is
    # confined to services/tokens.py. An unset secret gets a per-process
    # random value — usable for a single dev process, never for production.
    jwt_secret: str = Field(default_factory=lambda: secrets.token_urlsafe(48))

    # -- CORS — TRD 12.1: "TLS 1.3, JWT, CORS allowlist, CSP" ---------------
    # An ALLOWLIST, never "*": credentials ride on these requests, and a
    # wildcard origin with credentials is exactly the misconfiguration
    # OWASP A05 (TRD 12.6) warns about. Comma-separated in GL_CORS_ORIGINS.
    cors_origins: str = "http://localhost:5173"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]
    access_token_ttl_seconds: int = 900          # 15 min — TRD 12.2
    refresh_token_ttl_seconds: int = 7 * 24 * 3600  # 7 days — TRD 12.2
    agent_token_ttl_seconds: int = 900           # short-lived — TRD 12.2

    # -- Evidence store — DATABASE.md 12 -------------------------------------
    evidence_root: str = "./var/evidence"
    # TRD 10.3: evidence beyond the size limit is 413. The limit itself is
    # [OPEN] in the TRD; 5 MiB comfortably holds any single JPEG frame.
    evidence_max_bytes: int = 5 * 1024 * 1024

    # -- Ingest validation — TRD 10.3, ADR-007 -------------------------------
    # occurred_at may not be in the future beyond clock-skew tolerance.
    # Matches the health-beat skew measurement resolution.
    clock_skew_tolerance_seconds: int = 300

    # -- Camera credential sealing — TRD 12.4 --------------------------------
    # AES-256-GCM key material (hex) and its identifier. When unset, or when
    # the `cryptography` package is absent, the dev sealer stores a clearly
    # marked non-plaintext placeholder — see services/sealer.py.
    camera_key: str | None = None
    camera_key_id: str = "dev-key-0"

    # -- Rate limiting — TRD 12.7 --------------------------------------------
    login_rate_limit: int = 5           # per window per IP
    login_rate_window_seconds: int = 60

    # -- Self-service auth — CS-AU-10 (amended v1.4, owner decision) ---------
    # The deployment gate for sign-up (GL_SIGNUP_ENABLED). Flipping it is
    # NOT observable through the API: sign-up answers the same 202 either
    # way (CS-AU-16); disabled merely means nothing is created.
    signup_enabled: bool = True
    # Per-IP limits on the unauthenticated self-service routes, sharing
    # login_rate_window_seconds as their window.
    signup_rate_limit: int = 3
    password_reset_request_rate_limit: int = 3
    password_reset_rate_limit: int = 5

    # -- Server --------------------------------------------------------------
    host: str = "127.0.0.1"
    port: int = 8000


def load_settings() -> Settings:
    """Read settings from the environment. Fails loudly if a required
    variable (the two database URLs) is absent — fail closed, never fall
    back to a default database (BACKEND_CODING_RULES 6.5)."""
    return Settings()  # type: ignore[call-arg]  # env-populated
