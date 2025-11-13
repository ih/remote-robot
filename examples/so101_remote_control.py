#!/usr/bin/env python3
"""
Example: Remote SO-101 control.

Demonstrates using SO101Remote to control a remote SO-101 robot arm.
Requires SO-101 server running on remote machine.
"""

import argparse
import time

from lerobot.robots.so101_follower import SO101FollowerConfig
from remote_robot import SO101Remote


def main():
    parser = argparse.ArgumentParser(description="SO-101 Remote Control Example")
    parser.add_argument(
        "--host",
        type=str,
        required=True,
        help="Remote host IP address (e.g., 192.168.1.100)"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=18862,
        help="Remote server port (default: 18862)"
    )
    args = parser.parse_args()

    print("SO-101 Remote Control Example")
    print("=" * 60)
    print(f"Remote host: {args.host}:{args.port}")

    # Configure SO-101 (config is for remote robot)
    config = SO101FollowerConfig(
        port="/dev/ttyUSB0",  # This is the port on the REMOTE machine
    )

    # Create remote robot client
    robot = SO101Remote(
        config=config,
        remote_host=args.host,
        remote_port=args.port,
    )

    try:
        # Connect
        print("\nConnecting to remote SO-101...")
        robot.connect(calibrate=True)
        print(f"Connected! is_connected={robot.is_connected}")

        # Print features
        print(f"\nObservation features: {robot.observation_features}")
        print(f"Action features: {robot.action_features}")

        # Get initial observation
        print("\nGetting initial observation...")
        obs = robot.get_observation()
        print(f"Initial positions: {list(obs.keys())}")

        # Move to neutral position (example)
        print("\nMoving to neutral position...")
        action = {
            "shoulder_pan.pos": 0.0,
            "shoulder_lift.pos": 0.0,
            "elbow_flex.pos": 0.0,
            "wrist_flex.pos": 0.0,
            "wrist_roll.pos": 0.0,
            "gripper.pos": 0.0,
        }
        robot.send_action(action)
        time.sleep(2)

        # Get observation after movement
        obs = robot.get_observation()
        print(f"Current positions after move:")
        for motor in action.keys():
            print(f"  {motor}: {obs.get(motor, 'N/A')}")

    finally:
        # Disconnect
        print("\nDisconnecting...")
        robot.disconnect()
        print("Done!")


if __name__ == "__main__":
    main()
