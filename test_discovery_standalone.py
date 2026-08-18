import asyncio
import logging
import sys
import shutil

logging.basicConfig(level=logging.DEBUG)

async def check_dependencies():
    if not shutil.which("ffprobe"):
        print("\n[!] CRITICAL ERROR: 'ffprobe' is not installed on this laptop!")
        print("    Camera discovery requires ffmpeg. Please install it:")
        print("    Ubuntu/Debian: sudo apt install ffmpeg")
        print("    Mac: brew install ffmpeg\n")
        sys.exit(1)
    else:
        print("[+] ffprobe is installed.")

async def test_ping(ip, port):
    print(f"[*] Testing TCP connection to {ip}:{port}...")
    try:
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(ip, port), timeout=2.0
        )
        writer.close()
        await writer.wait_closed()
        print(f"[+] TCP connection to {ip}:{port} SUCCEEDED!")
        return True
    except Exception as e:
        print(f"[-] TCP connection to {ip}:{port} FAILED: {e}")
        return False

async def main():
    await check_dependencies()
    
    ip = "192.168.0.20"
    port = 554
    
    is_open = await test_ping(ip, port)
    if not is_open:
        print("\n[!] The laptop cannot reach the camera on port 554.")
        print("    Possible reasons:")
        print("    1. The laptop is on a different Wi-Fi network than the camera.")
        print("    2. The camera is turned off or has a different IP address.")
        print("    3. A firewall or VPN is blocking local network access.")
        sys.exit(1)
        
    print("\n[*] Initializing RTSP scanner...")
    from src.guardian_lens.services.camera_discovery import RTSPProbeService
    service = RTSPProbeService()
    
    print(f"[*] Probing {ip}:{port} for RTSP streams...")
    cameras = await service._probe_port(ip, port)
    
    if not cameras:
        print("[-] No cameras found during probe.")
    else:
        for c in cameras:
            print(f"[+] FOUND: IP: {c.ip_address}, Path: {c.rtsp_path}, Res: {c.resolution}, Codec: {c.codec}")

if __name__ == "__main__":
    asyncio.run(main())
