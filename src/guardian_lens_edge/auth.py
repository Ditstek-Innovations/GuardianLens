"""Agent authentication against the control plane.

The agent principal is distinct from any user principal and carries no
review permission (TRD 4 MOD-12): even a compromised agent credential cannot
decide an event. The credential string ``slug:agent_id:secret`` arrives via
the ``GL_AGENT_CREDENTIAL`` environment variable — never a CLI argument
(argv is world-readable) and never logged.
"""

from __future__ import annotations

import logging

import httpx

__all__ = ["AgentAuthError", "AgentAuthenticator", "AGENT_CREDENTIAL_ENV"]

logger = logging.getLogger(__name__)

AGENT_CREDENTIAL_ENV = "GL_AGENT_CREDENTIAL"


class AgentAuthError(Exception):
    """Raised when an agent token cannot be obtained."""


class AgentAuthenticator:
    """Obtains and caches the agent bearer token; re-fetches on expiry."""

    def __init__(
        self, client: httpx.Client, api_base: str, credential: str
    ) -> None:
        if not credential:
            raise ValueError(
                f"agent credential is empty; set {AGENT_CREDENTIAL_ENV}"
            )
        self._client = client
        self._api_base = api_base.rstrip("/")
        self._credential = credential
        self._token: str | None = None

    def token(self) -> str:
        if self._token is not None:
            return self._token
        try:
            response = self._client.post(
                f"{self._api_base}/api/v1/auth/agent",
                json={"credential": self._credential},
            )
        except httpx.HTTPError as exc:
            raise AgentAuthError(f"agent auth request failed: {exc}") from exc
        if response.status_code != 200:
            # Deliberately no response body in the message: it must never
            # echo credential material into a log line.
            raise AgentAuthError(
                f"agent auth rejected: HTTP {response.status_code}"
            )
        try:
            token = response.json()["access_token"]
        except (KeyError, ValueError) as exc:
            raise AgentAuthError("agent auth response missing access_token") from exc
        self._token = str(token)
        return self._token

    def invalidate(self) -> None:
        """Drop the cached token (called on 401 so the next call re-auths)."""
        self._token = None

    def bearer_header(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.token()}"}
