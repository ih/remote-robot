#!/usr/bin/env python3
"""
Start Jetbot RPyC server - Standalone for Jetson Nano.

This script can be run directly on Jetbot without installing the full remote-robot package.
Only requires: rpyc, jetbot, opencv-python, numpy

Run this script on Jetbot hardware to enable remote control.

Usage:
    python run_jetbot_server.py [--port PORT] [--camera-width WIDTH] [--camera-height HEIGHT]
"""

import argparse
import sys
from pathlib import Path

# Add src to path so we can import the server module
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

from remote_robot.server.jetbot_server import start_jetbot_server, DEFAULT_JETBOT_PORT


def main():
    parser = argparse.ArgumentParser(description="Start Jetbot RPyC server")
    parser.add_argument(
        "--port",
        type=int,
        default=DEFAULT_JETBOT_PORT,
        help=f"RPyC server port (default: {DEFAULT_JETBOT_PORT})"
    )
    parser.add_argument(
        "--camera-width",
        type=int,
        default=224,
        help="Camera frame width (default: 224)"
    )
    parser.add_argument(
        "--camera-height",
        type=int,
        default=224,
        help="Camera frame height (default: 224)"
    )
    parser.add_argument(
        "--host",
        type=str,
        default="0.0.0.0",
        help="Host address to bind to (default: 0.0.0.0)"
    )
    args = parser.parse_args()

    print("\n" + "=" * 60)
    print("Jetbot RPyC Server")
    print("=" * 60)
    print(f"Port: {args.port}")
    print(f"Host: {args.host}")
    print(f"Camera: {args.camera_width}x{args.camera_height}")
    print("=" * 60)
    print("\nDependencies required:")
    print("  - rpyc")
    print("  - jetbot")
    print("  - opencv-python")
    print("  - numpy")
    print("\nNo LeRobot installation needed!")
    print("=" * 60)
    print("\nPress Ctrl+C to stop server\n")

    start_jetbot_server(
        port=args.port,
        host=args.host,
        camera_width=args.camera_width,
        camera_height=args.camera_height,
    )


if __name__ == "__main__":
    main()
