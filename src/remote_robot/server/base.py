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

            # Debug logging - Enhanced
            self.logger.info(f"{'='*70}")
            self.logger.info(f"[SERVER] ACTION RECEIVED")
            self.logger.info(f"[SERVER] Raw action: {action}")
            self.logger.info(f"[SERVER] Raw action types: {[(k, type(v).__name__) for k, v in action.items()]}")
            self.logger.info(f"[SERVER] Decoded action: {decoded_action}")
            self.logger.info(f"[SERVER] Decoded types: {[(k, type(v).__name__) for k, v in decoded_action.items()]}")
            self.logger.info(f"[SERVER] Robot instance: {type(self._robot).__name__}")
            self.logger.info(f"[SERVER] Robot connected: {self._robot.is_connected if hasattr(self._robot, 'is_connected') else 'unknown'}")
            self.logger.info(f"[SERVER] Robot calibrated: {self._robot.is_calibrated if hasattr(self._robot, 'is_calibrated') else 'unknown'}")

            # Get observation BEFORE sending action
            try:
                obs_before = self._robot.get_observation()
                motor_positions_before = {
                    k: v for k, v in obs_before.items()
                    if not k.startswith("observation.images") and k != "main"
                }
                self.logger.info(f"[SERVER] Motor positions BEFORE action:")
                for key, val in motor_positions_before.items():
                    self.logger.info(f"  {key}: {val}")
            except Exception as e:
                self.logger.warning(f"[SERVER] Could not get observation before action: {e}")
                motor_positions_before = {}

            # Check motor torque status BEFORE sending action
            try:
                if hasattr(self._robot, 'bus'):
                    self.logger.info(f"[SERVER] Checking motor torque status...")
                    torque_status = {}
                    for motor_name in self._robot.bus.motors:
                        try:
                            torque_enabled = self._robot.bus.read("Torque_Enable", motor_name)
                            torque_status[motor_name] = torque_enabled
                        except Exception as e:
                            torque_status[motor_name] = f"Error: {e}"
                    self.logger.info(f"[SERVER] Motor torque status: {torque_status}")

                    # Check if any motors have torque disabled
                    disabled_motors = [m for m, status in torque_status.items() if status == 0 or status == False]
                    if disabled_motors:
                        self.logger.warning(f"[SERVER] WARNING: Torque is DISABLED on motors: {disabled_motors}")
                        self.logger.warning(f"[SERVER] Motors will not move with torque disabled!")
            except Exception as e:
                self.logger.warning(f"[SERVER] Could not check torque status: {e}")

            # Send to robot
            self.logger.info(f"[SERVER] Calling robot.send_action()...")

            # Add detailed logging if this is an SO101Follower
            if hasattr(self._robot, 'bus'):
                try:
                    # Log what will be written
                    goal_pos = {key.removesuffix(".pos"): val for key, val in decoded_action.items() if key.endswith(".pos")}
                    self.logger.info(f"[SERVER] Goal positions to write: {goal_pos}")

                    # Call send_action and log any exceptions from the bus
                    result = self._robot.send_action(decoded_action)
                    self.logger.info(f"[SERVER] sync_write to Goal_Position completed")
                except Exception as e:
                    self.logger.error(f"[SERVER] Exception during send_action: {e}", exc_info=True)
                    raise
            else:
                result = self._robot.send_action(decoded_action)

            self.logger.info(f"[SERVER] robot.send_action() returned: {result}")
            self.logger.info(f"[SERVER] Result type: {type(result).__name__}")

            # Get observation AFTER sending action
            try:
                import time
                time.sleep(0.05)  # Brief delay to let motors start moving
                obs_after = self._robot.get_observation()
                motor_positions_after = {
                    k: v for k, v in obs_after.items()
                    if not k.startswith("observation.images") and k != "main"
                }
                self.logger.info(f"[SERVER] Motor positions AFTER action:")
                for key, val in motor_positions_after.items():
                    before_val = motor_positions_before.get(key, 0.0)
                    if isinstance(before_val, (int, float)) and isinstance(val, (int, float)):
                        delta = val - before_val
                        self.logger.info(f"  {key}: {val} (delta: {delta:+.3f})")
                    else:
                        self.logger.info(f"  {key}: {val}")
            except Exception as e:
                self.logger.warning(f"[SERVER] Could not get observation after action: {e}")

            self.logger.info(f"{'='*70}")

            return result

        except Exception as e:
            self.logger.error(f"[SERVER] Failed to send action: {e}", exc_info=True)
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
