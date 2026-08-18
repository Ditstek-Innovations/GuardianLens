import asyncio
from src.guardian_lens.services.camera_discovery import RTSPProbeService
import logging
logging.basicConfig(level=logging.DEBUG)

async def main():
    service = RTSPProbeService()
    res = await service.scan_subnet("192.168.0.0/24")
    for r in res:
        print(f"IP: {r.ip_address}, Path: {r.rtsp_path}, Res: {r.resolution}, Codec: {r.codec}")

if __name__ == "__main__":
    asyncio.run(main())
