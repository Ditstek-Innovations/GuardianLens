from __future__ import annotations

from datetime import timedelta

import httpx

from guardian_lens_edge.auth import AgentAuthenticator
from guardian_lens_edge.frames import Frame
from guardian_lens_edge.preview import PreviewPublisher

from tests.edge.conftest import at


def test_preview_publisher_throttles_each_camera() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/v1/auth/agent":
            return httpx.Response(200, json={"access_token": "token"})
        requests.append(request)
        return httpx.Response(204)

    client = httpx.Client(transport=httpx.MockTransport(handler))
    auth = AgentAuthenticator(client, "http://control.test", "site:agent:secret")
    publisher = PreviewPublisher(client, "http://control.test", auth, interval_seconds=1)

    publisher.publish(Frame("camera-1", at(0), "rtsp", 1, b"\xff\xd8a\xff\xd9"))
    publisher.publish(
        Frame("camera-1", at(0) + timedelta(milliseconds=500), "rtsp", 2, b"\xff\xd8b\xff\xd9")
    )
    publisher.publish(Frame("camera-1", at(0) + timedelta(seconds=1), "rtsp", 3, b"\xff\xd8c\xff\xd9"))

    assert len(requests) == 2
    assert requests[0].url.path == "/api/v1/agents/cameras/camera-1/preview"
    assert requests[0].headers["content-type"] == "image/jpeg"
    assert requests[0].headers["x-captured-at"]
    client.close()
