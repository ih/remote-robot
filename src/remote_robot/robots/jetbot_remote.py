"""
Jetbot robot with remote control via RPyC.

Provides LeRobot-compatible interface for remotely controlling Jetbot robots.
"""

import logging
from functools import cached_property
from typing import Any, Optional

from lerobot.robots.robot import Robot
from remote_robot.utils import DeviceAlreadyConnectedError, DeviceNotConnectedError
from remote_robot.robots.jetbot_config import JetbotConfig

from remote_robot.utils.remote_client import create_rpyc_connection, RemoteConnectionError
from remote_robot.utils.serialization import encode_action, decode_observation


logger = logging.getLogger(__name__)

DEFAULT_JETBOT_PORT = 18861


class JetbotRemote(Robot):
    """
    Jetbot robot with remote control via RPyC.

    Connects to a remote jetbot_server.py instance to control Jetbot hardware
    over the network. Compatible with LeRobot 0.4.2+ Robot API.

    Example:
        ```python
        from remote_robot import JetbotRemote, JetbotConfig

        config = JetbotConfig()
        robot = JetbotRemote(config, remote_host="192.168.68.51")
        robot.connect()

        # Control the robot
        robot.send_action({"left_motor.value": 0.3, "right_motor.value": 0.3})
        obs = robot.get_observation()

        robot.disconnect()
        ```
    """

    config_class = JetbotConfig
    name = "jetbot_remote"

    def __init__(
        self,
        config: JetbotConfig,
        remote_host: str,
        remote_port: int = DEFAULT_JETBOT_PORT,
    ):
        """
        Initialize Jetbot remote robot.

        Args:
            config: JetbotConfig instance
            remote_host: Remote host IP/hostname where jetbot_server.py is running
            remote_port: Port for remote connection (default: 18861)
        """
        super().__init__(config)
        self.config = config
        self.remote_host = remote_host
        self.remote_port = remote_port

        # RPyC connection
        self._conn = None

        logger.info(f"Jetbot configured for remote operation at {remote_host}:{remote_port}")

    @cached_property
    def observation_features(self) -> dict[str, type | tuple]:
        """
        Observation features from Jetbot.

        Returns:
            Dictionary with motor values and camera features
        """
        if self._conn is not None:
            try:
                return self._conn.root.exposed_get_observation_features()
            except:
                pass

        # Default Jetbot features
        return {
            "left_motor.value": float,
            "right_motor.value": float,
        }

    @cached_property
    def action_features(self) -> dict[str, type]:
        """
        Action features for Jetbot.

        Returns:
            Dictionary with motor control features
        """
        if self._conn is not None:
            try:
                return self._conn.root.exposed_get_action_features()
            except:
                pass

        # Default Jetbot features
        return {
            "left_motor.value": float,
            "right_motor.value": float,
        }

    @property
    def is_connected(self) -> bool:
        """Check if robot is connected."""
        if self._conn is None:
            return False
        try:
            return self._conn.root.exposed_is_connected()
        except:
            return False

    @property
    def is_calibrated(self) -> bool:
        """Jetbot doesn't require calibration."""
        return True

    def connect(self, calibrate: bool = True) -> None:
        """
        Connect to the remote Jetbot server.

        Args:
            calibrate: Ignored for Jetbot (no calibration needed)
        """
        if self.is_connected:
            raise DeviceAlreadyConnectedError(
                f"Jetbot is already connected. Do not run `robot.connect()` twice."
            )

        try:
            logger.info(f"Connecting to remote Jetbot at {self.remote_host}:{self.remote_port}")
            self._conn = create_rpyc_connection(
                host=self.remote_host,
                port=self.remote_port,
                timeout=30,
                retry_attempts=3,
            )

            # Call remote connect
            self._conn.root.exposed_connect(calibrate=False)
            logger.info("Remote Jetbot connected successfully")

        except Exception as e:
            self._conn = None
            raise RemoteConnectionError(f"Failed to connect to remote Jetbot: {e}")

    def disconnect(self) -> None:
        """Disconnect from the remote Jetbot server."""
        if not self.is_connected:
            raise DeviceNotConnectedError(
                f"Jetbot is not connected. Try running `robot.connect()` first."
            )

        try:
            logger.info("Disconnecting from remote Jetbot")
            if self._conn is not None:
                self._conn.root.exposed_disconnect()
                self._conn.close()
                self._conn = None
            logger.info("Remote Jetbot disconnected")
        except Exception as e:
            logger.error(f"Error disconnecting from remote Jetbot: {e}")
            raise

    def calibrate(self) -> None:
        """No-op for Jetbot (no calibration needed)."""
        logger.info("Jetbot does not require calibration")

    def configure(self) -> None:
        """No-op for Jetbot."""
        pass

    def send_action(self, action: dict[str, Any]) -> dict[str, Any]:
        """
        Send action to the remote Jetbot.

        Args:
            action: Dictionary with "left_motor.value" and "right_motor.value"

        Returns:
            The actual action that was sent
        """
        if not self.is_connected:
            raise DeviceNotConnectedError(
                f"Jetbot is not connected. Try running `robot.connect()` first."
            )

        try:
            # Encode action for network transfer
            encoded_action = encode_action(action)

            # Send to remote server
            result = self._conn.root.exposed_send_action(encoded_action)

            # Decode result
            return decode_observation(result) if result else action

        except Exception as e:
            logger.error(f"Error sending action to remote Jetbot: {e}")
            raise

    def get_observation(self) -> dict[str, Any]:
        """
        Get observation from the remote Jetbot.

        Returns:
            Dictionary with motor values and camera images (if configured)
        """
        if not self.is_connected:
            raise DeviceNotConnectedError(
                f"Jetbot is not connected. Try running `robot.connect()` first."
            )

        try:
            obs = self._conn.root.exposed_get_observation()
            return decode_observation(obs)

        except Exception as e:
            logger.error(f"Error getting observation from remote Jetbot: {e}")
            raise

    def __del__(self):
        """Cleanup on deletion."""
        try:
            if self.is_connected:
                self.disconnect()
        except:
            pass
