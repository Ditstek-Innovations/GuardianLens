"""Throttled edge-to-control-plane live-preview relay."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta

import httpx

from guardian_lens_edge.auth import AgentAuthenticator, AgentAuthError
from guardian_lens_edge.frames import Frame

__all__ = ["PreviewPublisher"]

logger = logging.getLogger(__name__)


class PreviewPublisher:
    """Send at most one JPEG per camera per interval; failures are non-fatal."""

    def __init__(
        self,
        client: httpx.Client,
        api_base: str,
        authenticator: AgentAuthenticator,
        *,
        interval_seconds: float = 1.0,
    ) -> None:
        if interval_seconds <= 0:
            raise ValueError("interval_seconds must be positive")
        self._client = client
        self._api_base = api_base.rstrip("/")
        self._auth = authenticator
        self._interval = timedelta(seconds=interval_seconds)
        self._last_sent: dict[str, datetime] = {}

    def publish(self, frame: Frame) -> None:
        if frame.image_bytes is None:
            return
        last_sent = self._last_sent.get(frame.camera_id)
        if last_sent is not None and frame.captured_at - last_sent < self._interval:
            return
        # Throttle attempts as well as successes so an unavailable control
        # plane cannot turn preview delivery into a tight retry loop.
        self._last_sent[frame.camera_id] = frame.captured_at
        try:
            response = self._post(frame)
            if response.status_code == 401:
                self._auth.invalidate()
                response = self._post(frame)
            if response.status_code != 204:
                logger.warning(
                    "live preview rejected: camera=%s status=%s",
                    frame.camera_id,
                    response.status_code,
                )
        except (httpx.HTTPError, AgentAuthError) as exc:
            logger.warning(
                "live preview unavailable: camera=%s error=%s",
                frame.camera_id,
                type(exc).__name__,
            )

    def _post(self, frame: Frame) -> httpx.Response:
        return self._client.post(
            f"{self._api_base}/api/v1/agents/cameras/{frame.camera_id}/preview",
            content=frame.image_bytes,
            headers={
                **self._auth.bearer_header(),
                "Content-Type": "image/jpeg",
                "X-Captured-At": frame.captured_at.isoformat(),
            },
            timeout=2.0,
        )
