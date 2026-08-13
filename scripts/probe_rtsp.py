#!/usr/bin/env python3
"""Sanity-check an RTSP stream from this box, the way the edge agent will see it.

CAMERA_ONBOARDING.md §3 and CAMERA_INTEGRATION.md §2 precondition 4 call for
an ffprobe/VLC check before anything else — this is that check, using the
same OpenCV backend RtspSource uses, for boxes that carry neither.

Usage:
    .venv/bin/python scripts/probe_rtsp.py 'rtsp://user:pass@192.168.1.50:554/stream1'
    GL_PROBE_URL='rtsp://...' .venv/bin/python scripts/probe_rtsp.py --url-env GL_PROBE_URL

The URL contains camera credentials; prefer --url-env over the positional
argument on any box where shell history is shared or logged.
"""

from __future__ import annotations

import argparse
import os
import sys
import time


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("url", nargs="?", help="rtsp://user:pass@host:554/path")
    parser.add_argument(
        "--url-env",
        help="Read the URL from this environment variable instead of argv",
    )
    parser.add_argument(
        "--frames", type=int, default=5, help="Frames to sample (default 5)"
    )
    parser.add_argument(
        "--timeout", type=float, default=15.0, help="Seconds to wait for the first frame"
    )
    args = parser.parse_args(argv)

    url = os.environ.get(args.url_env, "") if args.url_env else (args.url or "")
    if not url:
        parser.error("give a URL, either positionally or via --url-env")

    try:
        import cv2
    except ImportError:
        print(
            "opencv-python-headless is not installed: pip install -e '.[edge-camera]'",
            file=sys.stderr,
        )
        return 2

    redacted = url.split("@")[-1] if "@" in url else url
    print(f"connecting to rtsp://***@{redacted} ...")
    capture = cv2.VideoCapture(url, cv2.CAP_FFMPEG)
    if not capture.isOpened():
        print("FAILED: could not open the stream (bad URL, network, or credentials)")
        return 1

    width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = capture.get(cv2.CAP_PROP_FPS)
    print(f"opened: {width}x{height} @ {fps:.1f}fps (as reported by the stream)")

    ok_count = 0
    deadline = time.monotonic() + args.timeout
    while ok_count < args.frames and time.monotonic() < deadline:
        ok, frame = capture.read()
        if ok and frame is not None:
            ok_count += 1
            print(f"frame {ok_count}/{args.frames}: {frame.shape[1]}x{frame.shape[0]}")
        else:
            time.sleep(0.2)
    capture.release()

    if ok_count == 0:
        print("FAILED: stream opened but produced no decodable frames")
        return 1
    if ok_count < args.frames:
        print(f"PARTIAL: only {ok_count}/{args.frames} frames decoded within {args.timeout}s")
        return 1
    print(f"OK: {ok_count}/{args.frames} frames decoded — this URL is ready to register")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
