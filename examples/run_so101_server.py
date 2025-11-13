#!/usr/bin/env python3
"""
Start SO-101 RPyC server.

Run this script on the computer connected to SO-101 hardware to enable remote control.

Usage:
    python run_so101_server.py --port COM8
    python run_so101_server.py  # Uses COM8 by default
"""

import argparse

from lerobot.cameras.configs import CameraConfig
from lerobot.robots.so101_follower import SO101FollowerConfig
from remote_robot.server.so101_server import start_so101_server, DEFAULT_SO101_PORT


def main():
    parser = argparse.ArgumentParser(description="Start SO-101 RPyC server")
    parser.add_argument(
        "--port",
        type=str,
        default="COM8",
        help="Serial port for SO-101 (default: COM8)"
    )
    parser.add_argument(
        "--server-port",
        type=int,
        default=DEFAULT_SO101_PORT,
        help=f"RPyC server port (default: {DEFAULT_SO101_PORT})"
    )
    args = parser.parse_args()

    # Configure SO-101
    config = SO101FollowerConfig(
        port=args.port,
        disable_torque_on_disconnect=True,
        cameras={
            # Add cameras if needed
            # "wrist": CameraConfig(
            #     camera_index=0,
            #     fps=30,
            #     width=640,
            #     height=480,
            # )
        }
    )

    # Start server
    print("=" * 60)
    print("Starting SO-101 Server")
    print("=" * 60)
    print(f"Serial port: {args.port}")
    print(f"Server port: {args.server_port}")
    print("=" * 60)
    print("\nPress Ctrl+C to stop server\n")

    start_so101_server(
        config=config,
        port=args.server_port,
        host="0.0.0.0",  # Listen on all network interfaces
    )


if __name__ == "__main__":
    main()
