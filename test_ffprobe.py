import subprocess
import json

paths = [
    "stream1", "stream2", "stream", "Streaming/channels/1",
    "Streaming/channels/2", "live/ch0", "live/ch1",
    "h264/ch1/main/av_stream", "rtsp/ch1/main/av_stream",
    "media/video1", "axis-media/media.amp"
]

ips = ["192.168.0.138", "192.168.0.184"]

for ip in ips:
    print(f"Testing {ip}...")
    for path in paths:
        url = f"rtsp://{ip}:554/{path}"
        cmd = [
            "ffprobe",
            "-v", "error",
            "-select_streams", "v:0",
            "-show_entries", "stream=width,height,codec_name",
            "-of", "json",
            url,
        ]
        try:
            result = subprocess.run(cmd, capture_output=True, timeout=5)
            if result.returncode == 0:
                print(f"SUCCESS on {url}!")
                print(result.stdout.decode())
            else:
                err = result.stderr.decode().strip()
                if "401" in err:
                    print(f"AUTH REQUIRED on {url}: {err}")
                else:
                    pass # print(f"FAIL on {url}: {err}")
        except subprocess.TimeoutExpired:
            pass # print(f"TIMEOUT on {url}")
