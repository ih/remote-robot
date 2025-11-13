"""
Base RPyC service for robot servers.

Provides common lifecycle management and safety features.
"""

import logging
from abc import ABC, abstractmethod
from typing import Any

import rpyc
from rpyc.core.protocol import Connection

from remote_robot.utils.serialization import encode_observation, decode_action


logger = logging.getLogger(__name__)


class BaseRobotServer(rpyc.Service, ABC):
    """
    Base RPyC service for robot servers.

    Provides:
    - Connection lifecycle management (on_connect, on_disconnect)
    - Lazy robot initialization
    - Common exposed methods for LeRobot Robot API
    - Automatic cleanup on client disconnect
    """

    def __init__(self):
        super().__init__()
        self._robot = None
        self.logger = logging.getLogger(self.__class__.__name__)

    @abstractmethod
    def _initialize_robot(self):
        """
        Initialize robot hardware.

        Must be implemented by subclass to create and connect robot instance.
        Should set self._robot to a LeRobot-compatible Robot instance.
        """
        pass

    @abstractmethod
    def _cleanup_robot(self):
        """
        Clean up robot hardware.

        Must be implemented by subclass to safely disconnect and cleanup robot.
        Called automatically on client disconnect.
        """
        pass

    def on_connect(self, conn: Connection):
        """Called when client connects."""
        self.logger.info(f"Client connected from {conn}")

    def on_disconnect(self, conn: Connection):
        """Called when client disconnects - ensures safe cleanup."""
        self.logger.info(f"Client disconnected from {conn}")
        try:
            self._cleanup_robot()
        except Exception as e:
            self.logger.error(f"Error during cleanup: {e}")

    # ===== LeRobot Robot API Methods =====
    # These are exposed to RPyC clients

    def exposed_connect(self, calibrate: bool = True) -> None:
        """
        Connect to robot hardware.

        Args:
            calibrate: Whether to calibrate robot if needed
        """
        try:
            if self._robot is None:
                self.logger.info("Initializing robot")
                self._initialize_robot()

            self.logger.info(f"Connecting robot (calibrate={calibrate})")
            self._robot.connect(calibrate=calibrate)
            self.logger.info("Robot connected successfully")

        except Exception as e:
            self.logger.error(f"Failed to connect robot: {e}")
            raise

    def exposed_disconnect(self) -> None:
        """Disconnect from robot hardware."""
        try:
            if self._robot is not None:
                self.logger.info("Disconnecting robot")
                self._robot.disconnect()
                self.logger.info("Robot disconnected")
        except Exception as e:
            self.logger.error(f"Failed to disconnect robot: {e}")
            raise

    def exposed_calibrate(self) -> None:
        """Calibrate the robot."""
        try:
            if self._robot is None:
                raise RuntimeError("Robot not initialized")
            self.logger.info("Calibrating robot")
            self._robot.calibrate()
            self.logger.info("Calibration complete")
        except Exception as e:
            self.logger.error(f"Calibration failed: {e}")
            raise

    def exposed_configure(self) -> None:
        """Apply runtime configuration to robot."""
        try:
            if self._robot is None:
                raise RuntimeError("Robot not initialized")
            self._robot.configure()
        except Exception as e:
            self.logger.error(f"Configuration failed: {e}")
            raise

    def exposed_get_observation(self) -> dict[str, Any]:
        """
        Get current robot observation.

        Returns:
            Encoded observation dictionary (with images as base64 strings)
        """
        try:
            if self._robot is None:
                raise RuntimeError("Robot not initialized")

            # Get observation from robot
            obs = self._robot.get_observation()

            # Encode for network transfer
            encoded_obs = encode_observation(obs)

            return encoded_obs

        except Exception as e:
            self.logger.error(f"Failed to get observation: {e}")
            raise

    def exposed_send_action(self, action: dict[str, Any]) -> dict[str, Any]:
        """
        Send action command to robot.

        Args:
            action: Action dictionary (may be encoded)

        Returns:
            Actual action sent by robot (after safety clipping)
        """
        try:
            if self._robot is None:
                raise RuntimeError("Robot not initialized")

            # Decode action (handles numpy arrays if encoded)
            decoded_action = decode_action(action)

            # Send to robot
            result = self._robot.send_action(decoded_action)

            return result

        except Exception as e:
            self.logger.error(f"Failed to send action: {e}")
            raise

    def exposed_is_connected(self) -> bool:
        """Check if robot is connected."""
        try:
            if self._robot is None:
                return False
            return self._robot.is_connected
        except Exception as e:
            self.logger.error(f"Failed to check connection status: {e}")
            return False

    def exposed_is_calibrated(self) -> bool:
        """Check if robot is calibrated."""
        try:
            if self._robot is None:
                return False
            return self._robot.is_calibrated
        except Exception as e:
            self.logger.error(f"Failed to check calibration status: {e}")
            return False

    def exposed_get_observation_features(self) -> dict[str, type | tuple]:
        """Get observation feature definitions."""
        try:
            if self._robot is None:
                raise RuntimeError("Robot not initialized")
            return dict(self._robot.observation_features)
        except Exception as e:
            self.logger.error(f"Failed to get observation features: {e}")
            raise

    def exposed_get_action_features(self) -> dict[str, type]:
        """Get action feature definitions."""
        try:
            if self._robot is None:
                raise RuntimeError("Robot not initialized")
            return dict(self._robot.action_features)
        except Exception as e:
            self.logger.error(f"Failed to get action features: {e}")
            raise
