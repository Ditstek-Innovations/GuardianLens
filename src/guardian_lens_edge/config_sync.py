"""Configuration sync — ADR-008: pull-only, conditional, last-known-good.

The agent pulls ``GET /api/v1/agents/{id}/config`` with ``If-None-Match``.
On 200 the document is validated (pydantic), applied atomically, and
persisted to the ``agent_config`` table so a restart does not lose it. On
304 nothing changes. On ANY failure — network, 5xx, auth, malformed or
invalid document — the last-known-good configuration is retained, the error
is logged and recorded, and the mismatch is visible in health (the applied
``config_version`` the agent reports is the fact; the control plane's view
is only the intention, RS-4).

There is NEVER a fallback to a default rule set: a default that activates
anything violates BR-001, and one that deactivates everything silently would
misstate the site's monitored scope. Absence of configuration means no rules
and therefore no candidates.
"""

from __future__ import annotations

import logging
from datetime import datetime

import httpx
from pydantic import ValidationError

from guardian_lens_edge.auth import AgentAuthenticator, AgentAuthError
from guardian_lens_edge.config import AgentConfig, normalise_document
from guardian_lens_edge.store import EdgeStore

__all__ = ["ConfigSync"]

logger = logging.getLogger(__name__)


class ConfigSync:
    def __init__(
        self,
        store: EdgeStore,
        client: httpx.Client,
        api_base: str,
        agent_id: str,
        authenticator: AgentAuthenticator,
    ) -> None:
        self._store = store
        self._client = client
        self._api_base = api_base.rstrip("/")
        self._agent_id = agent_id
        self._auth = authenticator
        self._applied: AgentConfig | None = None
        self._etag: str | None = None
        self.last_fetch_error: str | None = None

    @property
    def applied(self) -> AgentConfig | None:
        return self._applied

    @property
    def applied_version(self) -> int | None:
        return self._applied.config_version if self._applied else None

    def load_last_known_good(self) -> AgentConfig | None:
        """Restore the persisted configuration on startup.

        A document that validated when applied but no longer does (schema
        drift across an agent upgrade) is treated as absent, loudly — not
        patched into shape, which would be inventing configuration.
        """
        row = self._store.load_config()
        if row is None:
            return None
        try:
            self._applied = AgentConfig.model_validate(
                normalise_document(row.document)
            )
        except ValidationError as exc:
            logger.error(
                "persisted configuration no longer validates; treating as "
                "absent: %s",
                exc,
            )
            return None
        self._etag = f'"{row.config_version}"'
        self.last_fetch_error = row.last_fetch_error
        return self._applied

    def tick(self, now: datetime) -> AgentConfig | None:
        """One pull. Returns the configuration applied after the pull."""
        fetched_at = now.isoformat(timespec="seconds")
        headers: dict[str, str] = {}
        try:
            headers.update(self._auth.bearer_header())
            if self._etag is not None:
                headers["If-None-Match"] = self._etag
            response = self._client.get(
                f"{self._api_base}/api/v1/agents/{self._agent_id}/config",
                headers=headers,
            )
            if response.status_code == 401:
                self._auth.invalidate()
                headers.update(self._auth.bearer_header())
                response = self._client.get(
                    f"{self._api_base}/api/v1/agents/{self._agent_id}/config",
                    headers=headers,
                )
        except (httpx.HTTPError, AgentAuthError) as exc:
            self._record_failure(f"{type(exc).__name__}: {exc}", fetched_at)
            return self._applied

        if response.status_code == 304:
            self.last_fetch_error = None
            self._store.record_fetch_result(fetched_at=fetched_at, error=None)
            return self._applied
        if response.status_code != 200:
            self._record_failure(f"HTTP {response.status_code}", fetched_at)
            return self._applied

        try:
            document = response.json()
            config = AgentConfig.model_validate(normalise_document(document))
        except (ValueError, ValidationError) as exc:
            # Invalid document: retain last-known-good (ADR-008). Applying a
            # partially-understood document could silently activate or
            # deactivate rules — worse than staying one version behind.
            self._record_failure(f"invalid config document: {exc}", fetched_at)
            return self._applied

        # Apply atomically: the persisted row and the in-memory rule set
        # change together, and the ETag only advances on success.
        self._store.save_config(
            config.config_version, document, applied_at=fetched_at
        )
        self._applied = config
        self._etag = response.headers.get(
            "etag", f'"{config.config_version}"'
        )
        self.last_fetch_error = None
        logger.info(
            "configuration applied: config_version=%s rules=%d cameras=%d",
            config.config_version,
            len(config.rules),
            len(config.cameras),
        )
        return self._applied

    def _record_failure(self, error: str, fetched_at: str) -> None:
        self.last_fetch_error = error
        self._store.record_fetch_result(fetched_at=fetched_at, error=error)
        logger.warning(
            "config fetch failed; retaining last-known-good "
            "(applied_version=%s): %s",
            self.applied_version,
            error,
        )
