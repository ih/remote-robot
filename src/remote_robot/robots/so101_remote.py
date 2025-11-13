"""
SO-101 robot wrapper with optional remote control via RPyC.

Provides drop-in replacement for lerobot.robots.so101_follower.SO101Follower
with added remote control capability.
"""

import logging
from functools import cached_property
from typing import Any, Optional

from lerobot.robots.utils import RobotConfig
from lerobot.robots.robot import Robot
from remote_robot.utils import DeviceAlreadyConnectedError, DeviceNotConnectedError
from lerobot.robots.so101_follower import SO101Follower, SO101FollowerConfig

from remote_robot.utils.remote_client import create_rpyc_connection, RemoteConnectionError
from remote_robot.utils.serialization import encode_action, decode_observation


logger = logging.getLogger(__name__)

DEFAULT_SO101_PORT = 18862


class SO101Remote(Robot):
    """
    SO-101 robot with optional remote control.

    Can operate in two modes:
    1. Local mode (remote_host=None): Direct pass-through to SO101Follower
    2. Remote mode (remote_host specified): RPyC client to remote SO-101 server

    Drop-in compatible with LeRobot's SO101Follower.

    Example (Local):
        ```python
        from remote_robot import SO101Remote
        from lerobot.robots.so101_follower import SO101FollowerConfig

        config = SO101FollowerConfig(port="/dev/ttyUSB0")
        robot = SO101Remote(config)  # Local mode
        robot.connect()
        ```

    Example (Remote):
        ```python
        from remote_robot import SO101Remote
        from lerobot.robots.so101_follower import SO101FollowerConfig

        config = SO101FollowerConfig(port="/dev/ttyUSB0")
        robot = SO101Remote(config, remote_host="192.168.1.100")  # Remote mode
        robot.connect()
        ```
    """

    config_class = SO101FollowerConfig
    name = "so101_remote"

    def __init__(
        self,
        config: SO101FollowerConfig,
        remote_host: Optional[str] = None,
        remote_port: int = DEFAULT_SO101_PORT,
    ):
        """
        Initialize SO-101 robot wrapper.

        Args:
            config: SO101FollowerConfig (same as LeRobot SO101Follower)
            remote_host: Optional remote host IP/hostname. If None, uses local mode.
            remote_port: Port for remote connection (default: 18862)
        """
        super().__init__(config)
        self.config = config
        self.remote_host = remote_host
        self.remote_port = remote_port

        # Local or remote robot instance
        self._robot = None  # SO101Follower instance (local mode)
        self._conn = None  # RPyC connection (remote mode)
        self._is_remote = remote_host is not None

        if self._is_remote:
            logger.info(f"SO-101 configured for remote operation at {remote_host}:{remote_port}")
        else:
            logger.info("SO-101 configured for local operation")

    @cached_property
    def observation_features(self) -> dict[str, type | tuple]:
        """
        Observation features from SO-101.

        Delegates to underlying SO101Follower or remote server.
        """
        if self._is_remote:
            # Get from remote server
            if self._conn is not None:
                return self._conn.root.get_observation_features()
            else:
                # Default SO-101 features (6 motors + cameras)
                return {
                    "shoulder_pan.pos": float,
                    "shoulder_lift.pos": float,
                    "elbow_flex.pos": float,
                    "wrist_flex.pos": float,
                    "wrist_roll.pos": float,
                    "gripper.pos": float,
                }
        else:
            # Get from local robot
            if self._robot is not None:
                return self._robot.observation_features
            else:
                # Will be populated after connect()
                return {}

    @cached_property
    def action_features(self) -> dict[str, type]:
        """
        Action features for SO-101.

        Delegates to underlying SO101Follower or remote server.
        """
        if self._is_remote:
            # Get from remote server
            if self._conn is not None:
                return self._conn.root.get_action_features()
            else:
                # Default SO-101 features (6 motor positions)
                return {
                    "shoulder_pan.pos": float,
                    "shoulder_lift.pos": float,
                    "elbow_flex.pos": float,
                    "wrist_flex.pos": float,
                    "wrist_roll.pos": float,
                    "gripper.pos": float,
                }
        else:
            # Get from local robot
            if self._robot is not None:
                return self._robot.action_features
            else:
                # Will be populated after connect()
                return {}

    @property
    def is_connected(self) -> bool:
        """Check if robot is connected."""
        if self._is_remote:
            return self._conn is not None
        else:
            return self._robot is not None and self._robot.is_connected

    @property
    def is_calibrated(self) -> bool:
        """Check if robot is calibrated."""
        if self._is_remote:
            if self._conn is not None:
                return self._conn.root.is_calibrated()
            return False
        else:
            if self._robot is not None:
                return self._robot.is_calibrated
            return False

    def connect(self, calibrate: bool = True) -> None:
        """
        Connect to SO-101 robot.

        Args:
            calibrate: Whether to calibrate if needed

        Raises:
            DeviceAlreadyConnectedError: If already connected
            RemoteConnectionError: If remote connection fails
        """
        if self.is_connected:
            raise DeviceAlreadyConnectedError(f"{self.name} already connected")

        logger.info(f"Connecting to {self.name}")

        if self._is_remote:
            # Remote mode: connect via RPyC
            try:
                self._conn = create_rpyc_connection(
                    self.remote_host,
                    self.remote_port,
                    timeout=30,
                    retry_attempts=3,
                )
                # Initialize remote robot
                self._conn.root.connect(calibrate=calibrate)
                logger.info(f"Connected to remote SO-101 at {self.remote_host}:{self.remote_port}")
            except Exception as e:
                logger.error(f"Failed to connect to remote SO-101: {e}")
                raise
        else:
            # Local mode: create SO101Follower instance
            self._robot = SO101Follower(self.config)
            self._robot.connect(calibrate=calibrate)
            logger.info("Connected to local SO-101")

    def calibrate(self) -> None:
        """Calibrate the robot."""
        if not self.is_connected:
            raise DeviceNotConnectedError(f"{self.name} is not connected")

        if self._is_remote:
            self._conn.root.calibrate()
        else:
            self._robot.calibrate()

    def configure(self) -> None:
        """Apply runtime configuration."""
        if not self.is_connected:
            raise DeviceNotConnectedError(f"{self.name} is not connected")

        if self._is_remote:
            self._conn.root.configure()
        else:
            self._robot.configure()

    def get_observation(self) -> dict[str, Any]:
        """
        Get current robot observation.

        Returns:
            Dictionary with motor positions and camera images
        """
        if not self.is_connected:
            raise DeviceNotConnectedError(f"{self.name} is not connected")

        if self._is_remote:
            # Get encoded observation from remote
            encoded_obs = self._conn.root.get_observation()
            # Decode (handles image deserialization)
            return decode_observation(encoded_obs)
        else:
            return self._robot.get_observation()

    def send_action(self, action: dict[str, Any]) -> dict[str, Any]:
        """
        Send action to robot.

        Args:
            action: Dictionary with motor position commands

        Returns:
            Actual action sent (after safety clipping)
        """
        if not self.is_connected:
            raise DeviceNotConnectedError(f"{self.name} is not connected")

        if self._is_remote:
            # Encode action for network transfer
            encoded_action = encode_action(action)
            # Send to remote
            encoded_result = self._conn.root.send_action(encoded_action)
            return encoded_result
        else:
            return self._robot.send_action(action)

    def disconnect(self) -> None:
        """Disconnect from robot."""
        if not self.is_connected:
            raise DeviceNotConnectedError(f"{self.name} is not connected")

        logger.info(f"Disconnecting from {self.name}")

        if self._is_remote:
            # Disconnect remote
            self._conn.root.disconnect()
            self._conn.close()
            self._conn = None
            logger.info("Disconnected from remote SO-101")
        else:
            # Disconnect local
            self._robot.disconnect()
            self._robot = None
            logger.info("Disconnected from local SO-101")
