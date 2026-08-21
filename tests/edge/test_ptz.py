from __future__ import annotations

import httpx

from guardian_lens_edge.ptz import OnvifPtzController


def test_onvif_ptz_discovers_profile_moves_and_stops() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        body = request.content.decode("utf-8")
        if "GetCapabilities" in body:
            content = b"""<s:Envelope xmlns:s='http://www.w3.org/2003/05/soap-envelope'>
              <s:Body><Capabilities><Media><XAddr>http://camera:2020/media</XAddr></Media>
              <PTZ><XAddr>http://camera:2020/ptz</XAddr></PTZ></Capabilities></s:Body>
            </s:Envelope>"""
        elif "GetProfiles" in body:
            content = b"""<s:Envelope xmlns:s='http://www.w3.org/2003/05/soap-envelope'>
              <s:Body><Profiles token='profile-1'/></s:Body></s:Envelope>"""
        else:
            content = b"""<s:Envelope xmlns:s='http://www.w3.org/2003/05/soap-envelope'>
              <s:Body/></s:Envelope>"""
        return httpx.Response(200, content=content)

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        OnvifPtzController(client, duration_seconds=0).move(
            "rtsp://camera-user:camera-password@camera:554/stream1", "left"
        )

    bodies = [request.content.decode("utf-8") for request in requests]
    assert len(requests) == 4
    assert "GetCapabilities" in bodies[0]
    assert "GetProfiles" in bodies[1]
    assert 'PanTilt x="-0.45" y="0.0"' in bodies[2]
    assert "ContinuousMove" in bodies[2]
    assert "Stop" in bodies[3]
    assert all("camera-password" not in body for body in bodies)
