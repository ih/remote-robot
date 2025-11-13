"""
Jetbot differential drive robot compatible with LeRobot 0.4.2+ API.
"""

import logging
from functools import cached_property
from typing import Any

import numpy as np

from lerobot.common.robot_devices.cameras.utils import make_cameras_from_configs
from lerobot.common.robot_devices.robots.robot import Robot
from lerobot.common.robot_devices.utils import DeviceAlreadyConnectedError, DeviceNotConnectedError
from remote_robot.robots.jetbot_config import JetbotConfig


logger = logging.getLogger(__name__)


class Jetbot(Robot):
    """
    Jetbot differential drive robot with LeRobot API compatibility.

    Uses the jetbot package for hardware control (when mock=False).
    Compatible with LeRobot 0.4.2+ for dataset collection and teleoperation.

    The action/observation interface uses normalized motor values in range [-1, 1]
    matching the jetbot.Robot.set_motors() API.

    Example:
        ```python
        from remote_robot import Jetbot, JetbotConfig
        from lerobot.common.robot_devices.cameras.configs import OpenCVCameraConfig

        config = JetbotConfig(
            mock=False,
            cameras={
                "main": OpenCVCameraConfig(camera_index=0, fps=30, width=224, height=224)
            }
        )
        robot = Jetbot(config)
        robot.connect()

        # Get observation
        obs = robot.get_observation()
        # obs = {"left_motor.value": 0.0, "right_motor.value": 0.0, "main": np.ndarray(...)}

        # Send action (normalized speeds in [-1, 1])
        robot.send_action({"left_motor.value": 0.5, "right_motor.value": 0.5})  # Forward

        robot.disconnect()
        ```
    """

    config_class = JetbotConfig
    name = "jetbot"

    def __init__(self, config: JetbotConfig):
        super().__init__(config)
        self.config = config

        # Hardware interface (jetbot.Robot or mock)
        self._robot = None
        self._mock = config.mock

        # Current motor values (for observation)
        self._left_value = 0.0
        self._right_value = 0.0

        # Cameras (LeRobot standard)
        self.cameras = make_cameras_from_configs(config.cameras)

    @cached_property
    def observation_features(self) -> dict[str, type | tuple]:
        """
        Observation features for Jetbot.

        Returns:
            Dictionary with:
            - "left_motor.value": float - Left motor value in [-1, 1]
            - "right_motor.value": float - Right motor value in [-1, 1]
            - camera keys: (height, width, channels) tuples
        """
        obs_features = {
            "left_motor.value": float,
            "right_motor.value": float,
        }

        # Add camera features
        for cam_key, cam in self.cameras.items():
            obs_features[cam_key] = (cam.height, cam.width, cam.channels)

        return obs_features

    @cached_property
    def action_features(self) -> dict[str, type]:
        """
        Action features for Jetbot.

        Uses normalized motor values matching jetbot.Robot.set_motors() API.

        Returns:
            Dictionary with:
            - "left_motor.value": float - Left motor speed command in [-1, 1]
            - "right_motor.value": float - Right motor speed command in [-1, 1]
        """
        return {
            "left_motor.value": float,
            "right_motor.value": float,
        }

    @property
    def is_connected(self) -> bool:
        """Check if robot motors and cameras are connected."""
        motors_connected = self._robot is not None
        cameras_connected = all(cam.is_connected for cam in self.cameras.values())
        return motors_connected and cameras_connected

    @property
    def is_calibrated(self) -> bool:
        """Jetbot doesn't require calibration."""
        return True

    def connect(self, calibrate: bool = True) -> None:
        """
        Connect to Jetbot hardware.

        Args:
            calibrate: Ignored for Jetbot (no calibration needed)

        Raises:
            DeviceAlreadyConnectedError: If already connected
        """
        if self.is_connected:
            raise DeviceAlreadyConnectedError(f"{self.name} already connected")

        logger.info(f"Connecting to {self.name} (mock={self._mock})")

        # Connect to motors
        if self._mock:
            logger.info("Using mock motor interface")
            self._robot = _MockJetbotRobot()
        else:
            try:
                from jetbot import Robot as JetbotRobot

                logger.info("Connecting to Jetbot hardware")
                self._robot = JetbotRobot()
            except ImportError:
                raise ImportError(
                    "jetbot package not found. Install with: pip install jetbot "
                    "(or use mock=True for testing)"
                )

        # Initialize motors stopped
        self._robot.set_motors(0.0, 0.0)
        self._left_value = 0.0
        self._right_value = 0.0

        # Connect cameras
        for cam_key, cam in self.cameras.items():
            logger.info(f"Connecting camera: {cam_key}")
            cam.connect()

        self.configure()
        logger.info(f"{self.name} connected successfully")

    def calibrate(self) -> None:
        """Jetbot doesn't require calibration."""
        pass

    def configure(self) -> None:
        """Apply runtime configuration."""
        # No special configuration needed for Jetbot
        pass

    def get_observation(self) -> dict[str, Any]:
        """
        Get current robot state.

        Returns:
            Dictionary with motor values and camera images
        """
        if not self.is_connected:
            raise DeviceNotConnectedError(f"{self.name} is not connected")

        obs_dict = {
            "left_motor.value": self._left_value,
            "right_motor.value": self._right_value,
        }

        # Read cameras
        for cam_key, cam in self.cameras.items():
            obs_dict[cam_key] = cam.async_read()

        return obs_dict

    def send_action(self, action: dict[str, Any]) -> dict[str, Any]:
        """
        Send motor commands to robot.

        Args:
            action: Dictionary with "left_motor.value" and "right_motor.value" keys
                   Values should be in range [-1, 1]

        Returns:
            Dictionary with actual action sent (after clipping for safety)
        """
        if not self.is_connected:
            raise DeviceNotConnectedError(f"{self.name} is not connected")

        # Extract motor values
        left_value = action["left_motor.value"]
        right_value = action["right_motor.value"]

        # Clip to valid range [-1, 1]
        left_value = np.clip(left_value, -1.0, 1.0)
        right_value = np.clip(right_value, -1.0, 1.0)

        # Send to motors
        self._robot.set_motors(left_value, right_value)

        # Store current values for observation
        self._left_value = left_value
        self._right_value = right_value

        return {
            "left_motor.value": left_value,
            "right_motor.value": right_value,
        }

    def disconnect(self) -> None:
        """Disconnect from robot and stop motors."""
        if not self.is_connected:
            raise DeviceNotConnectedError(f"{self.name} is not connected")

        logger.info(f"Disconnecting from {self.name}")

        # Stop motors
        self._robot.set_motors(0.0, 0.0)
        self._left_value = 0.0
        self._right_value = 0.0

        if self.config.disable_motors_on_disconnect and hasattr(self._robot, "stop"):
            self._robot.stop()

        self._robot = None

        # Disconnect cameras
        for cam_key, cam in self.cameras.items():
            logger.info(f"Disconnecting camera: {cam_key}")
            cam.disconnect()

        logger.info(f"{self.name} disconnected")


class _MockJetbotRobot:
    """Mock jetbot.Robot for testing without hardware."""

    def __init__(self):
        self._left_value = 0.0
        self._right_value = 0.0

    def set_motors(self, left: float, right: float) -> None:
        """Simulate setting motor speeds."""
        self._left_value = left
        self._right_value = right
        logger.debug(f"Mock Jetbot: set_motors(left={left:.2f}, right={right:.2f})")

    def stop(self) -> None:
        """Simulate stopping motors."""
        self.set_motors(0.0, 0.0)
        logger.debug("Mock Jetbot: stop()")
