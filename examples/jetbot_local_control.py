#!/usr/bin/env python3
"""
Example: Local Jetbot control.

Demonstrates using Jetbot robot class for local control (no server needed).
"""

import time

from lerobot.common.robot_devices.cameras.configs import OpenCVCameraConfig
from remote_robot import Jetbot, JetbotConfig


def main():
    print("Jetbot Local Control Example")
    print("=" * 60)

    # Configure Jetbot
    config = JetbotConfig(
        mock=True,  # Set to False for real hardware
        cameras={
            # "main": OpenCVCameraConfig(
            #     camera_index=0,
            #     fps=30,
            #     width=224,
            #     height=224,
            # )
        }
    )

    # Create robot
    robot = Jetbot(config)

    try:
        # Connect
        print("Connecting to Jetbot...")
        robot.connect()
        print(f"Connected! is_connected={robot.is_connected}")

        # Print features
        print(f"\nObservation features: {robot.observation_features}")
        print(f"Action features: {robot.action_features}")

        # Drive forward
        print("\n1. Driving forward...")
        action = {"left_motor.value": 0.3, "right_motor.value": 0.3}
        robot.send_action(action)
        obs = robot.get_observation()
        print(f"Observation: {obs}")
        time.sleep(2)

        # Turn left
        print("\n2. Turning left...")
        action = {"left_motor.value": -0.3, "right_motor.value": 0.3}
        robot.send_action(action)
        obs = robot.get_observation()
        print(f"Observation: {obs}")
        time.sleep(2)

        # Stop
        print("\n3. Stopping...")
        action = {"left_motor.value": 0.0, "right_motor.value": 0.0}
        robot.send_action(action)
        obs = robot.get_observation()
        print(f"Observation: {obs}")

    finally:
        # Disconnect
        print("\nDisconnecting...")
        robot.disconnect()
        print("Done!")


if __name__ == "__main__":
    main()
