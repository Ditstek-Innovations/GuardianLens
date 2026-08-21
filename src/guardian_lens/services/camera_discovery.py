"""Camera discovery service - scans for RTSP cameras on network.

Implements RTSP endpoint detection and basic device information extraction.
Uses subprocess-based ffprobe for stream verification (TRD 12.6 A10: control
plane never initiates connections to cameras; discovery is read-only probe).
"""

from __future__ import annotations

import asyncio
import ipaddress
import logging
import os
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


def resolve_ffprobe() -> str:
    """Resolve system, configured, or repository-bundled ffprobe."""
    configured = os.environ.get("GL_FFPROBE_PATH") or os.environ.get(
        "GL_FFPROBE_BIN"
    )
    candidates = [
        configured,
        shutil.which("ffprobe"),
        str(Path(__file__).resolve().parents[3] / "var/ffmpeg/usr/bin/ffprobe"),
    ]
    for candidate in candidates:
        if candidate and Path(candidate).is_file() and os.access(candidate, os.X_OK):
            return candidate
    raise FileNotFoundError(
        "ffprobe was not found; install ffmpeg or set GL_FFPROBE_PATH"
    )


@dataclass
class DiscoveredCamera:
    """Result of a successful camera discovery probe."""

    ip_address: str
    port: int
    rtsp_path: str
    resolution: Optional[str] = None
    codec: Optional[str] = None
    model: Optional[str] = None
    manufacturer: Optional[str] = None


def anonymous_rtsp_url(ip_address: str, port: int, rtsp_path: str) -> str:
    """Build an RTSP URL with no camera login."""
    return camera_rtsp_url(ip_address, port, rtsp_path)


def camera_rtsp_url(
    ip_address: str,
    port: int,
    rtsp_path: str,
    *,
    username: str | None = None,
    password: str | None = None,
) -> str:
    """Build the URL that will be sealed onto a registered camera.

    The edge agent uses this stored URL — there is no second hardcoded
    stream. Username/password are optional; omit them only when the camera
    truly allows anonymous RTSP.
    """
    from urllib.parse import quote

    path = rtsp_path.strip().lstrip("/")
    host = ip_address.strip()
    origin = f"{host}:{int(port)}/{path}"
    user = (username or "").strip()
    secret = password or ""
    if user and secret:
        return f"rtsp://{quote(user, safe='')}:{quote(secret, safe='')}@{origin}"
    if user or secret:
        raise ValueError("RTSP username and password must both be set, or neither")
    return f"rtsp://{origin}"


class RTSPProbeService:
    """Detects RTSP cameras by probing common RTSP ports and paths.

    Strategy:
    1. For each IP in the subnet:
       - Probe port 554 (standard RTSP)
       - Probe port 8554 (common alternative)
       - Probe port 8080 (some cameras)
    2. For each reachable port, try common RTSP paths
    3. Extract stream info (resolution, codec) via ffprobe
    4. Return verified candidates
    """

    # Common RTSP paths tried in order (most likely first)
    DEFAULT_RTSP_PATHS = [
        "stream1",
        "stream2",
        "stream",
        "Streaming/channels/1",
        "Streaming/channels/2",
        "live/ch0",
        "live/ch1",
        "h264/ch1/main/av_stream",
        "rtsp/ch1/main/av_stream",
        "media/video1",
        "axis-media/media.amp",
    ]

    DEFAULT_PORTS = [554, 8554, 8080]
    PROBE_TIMEOUT = 3  # seconds per port probe
    FFPROBE_TIMEOUT = 5  # seconds for ffprobe analysis

    def __init__(self):
        self.logger = logger
        self._ffprobe = resolve_ffprobe()

    async def scan_subnet(
        self, subnet: str, timeout_per_host: int = 2
    ) -> list[DiscoveredCamera]:
        """Scan a subnet for RTSP cameras.

        Args:
            subnet: CIDR notation (e.g., "192.168.1.0/24")
            timeout_per_host: Seconds to spend probing each host

        Returns:
            List of discovered cameras with verified RTSP paths
        """
        try:
            network = ipaddress.IPv4Network(subnet, strict=False)
        except ValueError as e:
            self.logger.error(f"Invalid subnet: {subnet}: {e}")
            return []

        discovered = []
        hosts = list(network.hosts())

        self.logger.info(f"Scanning {len(hosts)} hosts in {subnet}")

        self.logger.info(f"Scanning {len(hosts)} hosts in {subnet} concurrently")

        # Scan in chunks to avoid opening too many sockets at once
        chunk_size = 50
        for i in range(0, len(hosts), chunk_size):
            chunk = hosts[i : i + chunk_size]
            tasks = [self._probe_host(str(host)) for host in chunk]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            for result in results:
                if isinstance(result, list):
                    discovered.extend(result)
                elif isinstance(result, Exception):
                    self.logger.error(f"Error in host probe task: {result}")

        self.logger.info(f"Discovery complete: found {len(discovered)} cameras")
        return discovered

    async def _probe_host(self, ip: str) -> list[DiscoveredCamera]:
        """Probe a single host for RTSP cameras.

        Tries common ports and paths in parallel, returns verified cameras.
        """
        tasks = [self._probe_port(ip, port) for port in self.DEFAULT_PORTS]

        results = await asyncio.gather(*tasks, return_exceptions=True)
        discovered = []

        for result in results:
            if isinstance(result, list):
                discovered.extend(result)

        return discovered

    async def _is_port_open(self, ip: str, port: int, timeout: float = 0.5) -> bool:
        """Check if a TCP port is open."""
        try:
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(ip, port), timeout=timeout
            )
            writer.close()
            await writer.wait_closed()
            return True
        except Exception:
            return False

    async def _probe_port(
        self, ip: str, port: int
    ) -> list[DiscoveredCamera]:
        """Probe a specific IP:port combination for RTSP endpoints."""
        discovered = []

        # Fast fail if port is closed
        if not await self._is_port_open(ip, port):
            return discovered
        auth_required_camera = None

        for path in self.DEFAULT_RTSP_PATHS:
            try:
                stream_url = anonymous_rtsp_url(ip, port, path)

                # Use asyncio timeout
                try:
                    info = await asyncio.wait_for(
                        self._verify_rtsp_stream(stream_url),
                        timeout=self.PROBE_TIMEOUT,
                    )

                    if info:
                        camera = DiscoveredCamera(
                            ip_address=ip,
                            port=port,
                            rtsp_path=path,
                            resolution=info.get("resolution"),
                            codec=info.get("codec"),
                        )

                        if info.get("resolution") == "Unknown (Auth Required)":
                            if not auth_required_camera:
                                auth_required_camera = camera
                        else:
                            discovered.append(camera)
                            self.logger.debug(f"Found camera at {stream_url}: {camera}")
                            break

                except asyncio.TimeoutError:
                    continue

            except Exception as e:
                self.logger.debug(
                    f"Error probing {ip}:{port}/{path}: {e}"
                )
                continue

        if not discovered and auth_required_camera:
            discovered.append(auth_required_camera)
            self.logger.debug(
                "Found auth-required camera at rtsp://%s:%s/%s",
                ip,
                port,
                auth_required_camera.rtsp_path,
            )

        return discovered

    async def _verify_rtsp_stream(self, rtsp_url: str) -> dict | None:
        """Verify RTSP stream is accessible and extract codec info.

        Uses ffprobe to test connectivity and gather stream metadata.
        Returns dict with resolution/codec or None if unreachable.
        """
        try:
            # ffprobe with short timeout for quick verification
            cmd = [
                self._ffprobe,
                "-v",
                "error",
                "-select_streams",
                "v:0",
                "-show_entries",
                "stream=width,height,codec_name",
                "-of",
                "json",
                rtsp_url,
            ]

            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=self.FFPROBE_TIMEOUT,
                )
            except asyncio.TimeoutError:
                process.kill()
                return None

            if process.returncode != 0:
                err_text = stderr.decode()
                if "401 Unauthorized" in err_text:
                    return {"resolution": "Unknown (Auth Required)", "codec": "Unknown"}
                return None

            import json

            try:
                data = json.loads(stdout.decode())
                streams = data.get("streams", [])
                if not streams:
                    return None

                stream = streams[0]
                width = stream.get("width")
                height = stream.get("height")
                codec = stream.get("codec_name")

                result = {}
                if width and height:
                    result["resolution"] = f"{width}x{height}"
                if codec:
                    result["codec"] = codec

                return result if result else None

            except json.JSONDecodeError:
                return None

        except FileNotFoundError:
            self.logger.error(
                "CRITICAL: ffprobe was not found. Camera discovery requires "
                "ffmpeg or GL_FFPROBE_PATH/GL_FFPROBE_BIN."
            )
            return None
        except Exception as e:
            self.logger.debug(f"ffprobe error for {rtsp_url}: {e}")
            return None

    async def probe_single_camera(
        self, ip: str, port: int = 554, rtsp_path: str = "stream1"
    ) -> Optional[DiscoveredCamera]:
        """Probe a single known camera location.

        Useful for manual verification or testing a specific endpoint.
        """
        cameras = await self._probe_port(ip, port)
        return next((c for c in cameras if c.rtsp_path == rtsp_path), None)
