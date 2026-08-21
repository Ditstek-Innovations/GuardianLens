"""ONVIF PTZ control executed only at the camera-side edge agent."""

from __future__ import annotations

import base64
import hashlib
import logging
import os
import time
from datetime import UTC, datetime
from urllib.parse import unquote, urlparse
from xml.etree import ElementTree

import httpx

from guardian_lens_edge.auth import AgentAuthenticator, AgentAuthError
from guardian_lens_edge.config_sync import ConfigSync
from guardian_lens_edge.unsealer import CredentialUnsealError, CredentialUnsealer

__all__ = ["OnvifPtzController", "PtzCommandPoller"]

logger = logging.getLogger(__name__)

_SOAP = "http://www.w3.org/2003/05/soap-envelope"
_WSSE = "http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-secext-1.0.xsd"
_WSU = "http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-utility-1.0.xsd"
_PASSWORD_DIGEST = (
    "http://docs.oasis-open.org/wss/2004/01/"
    "oasis-200401-wss-username-token-profile-1.0#PasswordDigest"
)
_BASE64_BINARY = (
    "http://docs.oasis-open.org/wss/2004/01/"
    "oasis-200401-wss-soap-message-security-1.0#Base64Binary"
)
_DIRECTION_VELOCITY = {
    "up": (0.0, 0.45),
    "down": (0.0, -0.45),
    "left": (-0.45, 0.0),
    "right": (0.45, 0.0),
}


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


class OnvifPtzController:
    """Discovers the camera's ONVIF services and performs one bounded move."""

    def __init__(self, client: httpx.Client, *, duration_seconds: float = 0.35) -> None:
        self._client = client
        self._duration = duration_seconds

    def move(self, stream_url: str, direction: str) -> None:
        if direction not in _DIRECTION_VELOCITY:
            raise ValueError("unsupported PTZ direction")
        parsed = urlparse(stream_url)
        if parsed.hostname is None or parsed.username is None or parsed.password is None:
            raise ValueError("camera URL must include host, username and password")
        username, password = unquote(parsed.username), unquote(parsed.password)
        device_url = f"http://{parsed.hostname}:2020/onvif/device_service"
        capabilities = self._soap(
            device_url,
            username,
            password,
            '<tds:GetCapabilities xmlns:tds="http://www.onvif.org/ver10/device/wsdl">'
            "<tds:Category>All</tds:Category></tds:GetCapabilities>",
        )
        ptz_url = self._xaddr(capabilities, "PTZ")
        media_url = self._xaddr(capabilities, "Media")
        profiles = self._soap(
            media_url,
            username,
            password,
            '<trt:GetProfiles xmlns:trt="http://www.onvif.org/ver10/media/wsdl"/>',
        )
        profile_token = next(
            (
                element.attrib["token"]
                for element in profiles.iter()
                if _local_name(element.tag) == "Profiles" and "token" in element.attrib
            ),
            None,
        )
        if profile_token is None:
            raise RuntimeError("camera returned no ONVIF media profile")
        pan, tilt = _DIRECTION_VELOCITY[direction]
        self._soap(
            ptz_url,
            username,
            password,
            '<tptz:ContinuousMove xmlns:tptz="http://www.onvif.org/ver20/ptz/wsdl" '
            'xmlns:tt="http://www.onvif.org/ver10/schema">'
            f"<tptz:ProfileToken>{profile_token}</tptz:ProfileToken>"
            f'<tptz:Velocity><tt:PanTilt x="{pan}" y="{tilt}"/></tptz:Velocity>'
            "</tptz:ContinuousMove>",
        )
        time.sleep(self._duration)
        self._soap(
            ptz_url,
            username,
            password,
            '<tptz:Stop xmlns:tptz="http://www.onvif.org/ver20/ptz/wsdl">'
            f"<tptz:ProfileToken>{profile_token}</tptz:ProfileToken>"
            "<tptz:PanTilt>true</tptz:PanTilt><tptz:Zoom>true</tptz:Zoom>"
            "</tptz:Stop>",
        )

    def _soap(self, url: str, username: str, password: str, body: str) -> ElementTree.Element:
        envelope = self._envelope(username, password, body)
        response = self._client.post(
            url,
            content=envelope.encode("utf-8"),
            headers={"Content-Type": "application/soap+xml; charset=utf-8"},
            timeout=5.0,
        )
        response.raise_for_status()
        root = ElementTree.fromstring(response.content)
        fault = next((item for item in root.iter() if _local_name(item.tag) == "Fault"), None)
        if fault is not None:
            raise RuntimeError("camera rejected the ONVIF PTZ command")
        return root

    @staticmethod
    def _xaddr(root: ElementTree.Element, service_name: str) -> str:
        for element in root.iter():
            if _local_name(element.tag) != service_name:
                continue
            for child in element.iter():
                if _local_name(child.tag) == "XAddr" and child.text:
                    return child.text
        raise RuntimeError(f"camera did not advertise ONVIF {service_name} service")

    @staticmethod
    def _envelope(username: str, password: str, body: str) -> str:
        nonce = os.urandom(16)
        created = datetime.now(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z")
        digest = base64.b64encode(
            hashlib.sha1(nonce + created.encode("utf-8") + password.encode("utf-8")).digest()
        ).decode("ascii")
        encoded_nonce = base64.b64encode(nonce).decode("ascii")
        return (
            f'<s:Envelope xmlns:s="{_SOAP}" xmlns:wsse="{_WSSE}" xmlns:wsu="{_WSU}">'
            '<s:Header><wsse:Security s:mustUnderstand="1"><wsse:UsernameToken>'
            f"<wsse:Username>{username}</wsse:Username>"
            f'<wsse:Password Type="{_PASSWORD_DIGEST}">{digest}</wsse:Password>'
            f'<wsse:Nonce EncodingType="{_BASE64_BINARY}">{encoded_nonce}</wsse:Nonce>'
            f"<wsu:Created>{created}</wsu:Created>"
            f"</wsse:UsernameToken></wsse:Security></s:Header><s:Body>{body}</s:Body>"
            "</s:Envelope>"
        )


class PtzCommandPoller:
    def __init__(
        self,
        client: httpx.Client,
        api_base: str,
        authenticator: AgentAuthenticator,
        config_sync: ConfigSync,
        unsealer: CredentialUnsealer,
        controller: OnvifPtzController | None = None,
    ) -> None:
        self._client = client
        self._api_base = api_base.rstrip("/")
        self._auth = authenticator
        self._config_sync = config_sync
        self._unsealer = unsealer
        self._controller = controller or OnvifPtzController(client)

    def tick(self) -> None:
        try:
            response = self._client.get(
                f"{self._api_base}/api/v1/agents/ptz-commands",
                headers=self._auth.bearer_header(),
            )
            if response.status_code == 401:
                self._auth.invalidate()
                response = self._client.get(
                    f"{self._api_base}/api/v1/agents/ptz-commands",
                    headers=self._auth.bearer_header(),
                )
            response.raise_for_status()
            commands = response.json()
        except (httpx.HTTPError, AgentAuthError, ValueError) as exc:
            logger.warning("PTZ command poll failed: %s", type(exc).__name__)
            return
        config = self._config_sync.applied
        if config is None:
            return
        cameras = {camera.camera_id: camera for camera in config.cameras}
        for command in commands:
            camera = cameras.get(str(command.get("camera_id", "")))
            if camera is None or camera.stream_url_sealed is None or camera.stream_url_key_id is None:
                logger.warning("PTZ command ignored: camera credential unavailable")
                continue
            try:
                stream_url = self._unsealer.unseal(
                    camera.stream_url_sealed, camera.stream_url_key_id
                ).reveal()
                self._controller.move(stream_url, str(command.get("direction", "")))
                logger.info("PTZ movement completed: camera=%s", camera.camera_id)
            except (CredentialUnsealError, httpx.HTTPError, RuntimeError, ValueError):
                logger.exception("PTZ movement failed: camera=%s", camera.camera_id)
