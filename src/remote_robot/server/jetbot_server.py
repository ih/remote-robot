"""
RPyC server for Jetbot robot - Python 3.5+ compatible version.

This server has minimal dependencies and does NOT require LeRobot.
Only requires: rpyc, jetbot, opencv-python, numpy

Run this script on Jetbot hardware to enable remote control.

Usage:
    python jetbot_server_py35.py
"""

import base64
import logging

import cv2
import numpy as np
import rpyc
from rpyc.utils.server import ThreadedServer


logger = logging.getLogger(__name__)

DEFAULT_JETBOT_PORT = 18861


class JetbotService(rpyc.Service):
    """
    Standalone RPyC service for Jetbot.

    Exposes motor control and camera access without LeRobot dependencies.
    Compatible with both the LeRobot client (remote_robot.Jetbot) and
    direct RPyC clients.
    """

    def __init__(self, camera_width=224, camera_height=224):
        """
        Initialize Jetbot service.

        Args:
            camera_width: Camera frame width
            camera_height: Camera frame height
        """
        super(JetbotService, self).__init__()
        self.robot = None
        self.camera = None
        self.camera_width = camera_width
        self.camera_height = camera_height

        # Current motor values (for observation)
        self._left_value = 0.0
        self._right_value = 0.0

        logger.info("JetbotService initialized (camera: {}x{})".format(
            camera_width, camera_height))

    def on_connect(self, conn):
        """Called when client connects."""
        logger.info("Client connected from {}".format(conn))

    def on_disconnect(self, conn):
        """Called when client disconnects - ensures safe cleanup."""
        logger.info("Client disconnected from {}".format(conn))
        try:
            # Stop camera
            if self.camera is not None:
                self.camera.stop()
                self.camera = None
                logger.info("Camera stopped")

            # Stop motors
            if self.robot is not None:
                self.robot.stop()
                logger.info("Motors stopped")
        except Exception as e:
            logger.error("Error during cleanup: {}".format(e))

    # ===== Simple Motor Control API =====

    def exposed_set_motors(self, left_speed, right_speed):
        """
        Set motor speeds (simple API for compatibility with reference server).

        Args:
            left_speed: Left motor speed in range [-1.0, 1.0]
            right_speed: Right motor speed in range [-1.0, 1.0]

        Returns:
            True on success
        """
        try:
            logger.debug("set_motors: left={}, right={}".format(left_speed, right_speed))

            # Lazy initialization
            if self.robot is None:
                from jetbot import Robot
                logger.debug("Initializing robot")
                self.robot = Robot()

            # Set motor values
            self.robot.left_motor.value = float(left_speed)
            self.robot.right_motor.value = float(right_speed)

            # Store for observation
            self._left_value = float(left_speed)
            self._right_value = float(right_speed)

            logger.debug("Motors set successfully")
            return True

        except Exception as e:
            logger.error("Error setting motors: {}".format(e))
            raise

    def exposed_get_camera_frame(self):
        """
        Get camera frame as base64-encoded JPEG.

        Returns:
            Base64-encoded JPEG string, or None on error
        """
        try:
            # Lazy initialization
            if self.camera is None:
                from jetbot import Camera
                logger.info("Initializing camera ({}x{})".format(
                    self.camera_width, self.camera_height))
                self.camera = Camera.instance(
                    width=self.camera_width,
                    height=self.camera_height
                )

            # Get frame from camera
            frame = self.camera.value

            # Encode as JPEG for efficient transfer
            _, buffer = cv2.imencode('.jpg', frame)

            # Convert to base64 string
            jpg_as_text = base64.b64encode(buffer).decode('utf-8')

            return jpg_as_text

        except Exception as e:
            logger.error("Error getting camera frame: {}".format(e))
            return None

    # ===== LeRobot-Compatible API =====
    # These methods allow the server to work with remote_robot.Jetbot client

    def exposed_connect(self, calibrate=True):
        """Connect to robot (LeRobot API compatibility)."""
        try:
            if self.robot is None:
                from jetbot import Robot
                logger.info("Connecting to Jetbot motors")
                self.robot = Robot()
            logger.info("Jetbot connected")
        except Exception as e:
            logger.error("Failed to connect: {}".format(e))
            raise

    def exposed_disconnect(self):
        """Disconnect from robot (LeRobot API compatibility)."""
        try:
            if self.robot is not None:
                logger.info("Disconnecting Jetbot")
                self.robot.stop()
            logger.info("Jetbot disconnected")
        except Exception as e:
            logger.error("Failed to disconnect: {}".format(e))
            raise

    def exposed_send_action(self, action):
        """
        Send action to robot (LeRobot API compatibility).

        Args:
            action: Dictionary with "left_motor.value" and "right_motor.value"

        Returns:
            Actual action sent
        """
        try:
            left = action.get("left_motor.value", 0.0)
            right = action.get("right_motor.value", 0.0)

            # Clip to valid range
            left = np.clip(left, -1.0, 1.0)
            right = np.clip(right, -1.0, 1.0)

            self.exposed_set_motors(left, right)

            return {
                "left_motor.value": left,
                "right_motor.value": right,
            }
        except Exception as e:
            logger.error("Failed to send action: {}".format(e))
            raise

    def exposed_get_observation(self):
        """
        Get observation from robot (LeRobot API compatibility).

        Returns:
            Dictionary with motor values and camera frame (base64 encoded)
        """
        try:
            obs = {
                "__type__": "observation",
                "left_motor.value": self._left_value,
                "right_motor.value": self._right_value,
            }

            # Initialize and get camera frame
            try:
                frame_b64 = self.exposed_get_camera_frame()
                if frame_b64:
                    obs["camera"] = {
                        "__type__": "image",
                        "data": frame_b64,
                        "shape": (self.camera_height, self.camera_width, 3),
                        "dtype": "uint8",
                    }
            except Exception as e:
                logger.warning("Failed to get camera frame: {}".format(e))
                # Continue without camera data

            return obs
        except Exception as e:
            logger.error("Failed to get observation: {}".format(e))
            raise

    def exposed_is_connected(self):
        """Check if robot is connected (LeRobot API compatibility)."""
        return self.robot is not None

    def exposed_is_calibrated(self):
        """Jetbot doesn't require calibration (LeRobot API compatibility)."""
        return True

    def exposed_calibrate(self):
        """No-op for Jetbot (LeRobot API compatibility)."""
        pass

    def exposed_configure(self):
        """No-op for Jetbot (LeRobot API compatibility)."""
        pass

    def exposed_get_observation_features(self):
        """Get observation feature definitions (LeRobot API compatibility)."""
        features = {
            "left_motor.value": "float",
            "right_motor.value": "float",
        }
        if self.camera is not None:
            features["camera"] = (self.camera_height, self.camera_width, 3)
        return features

    def exposed_get_action_features(self):
        """Get action feature definitions (LeRobot API compatibility)."""
        return {
            "left_motor.value": "float",
            "right_motor.value": "float",
        }


def start_jetbot_server(
    port=DEFAULT_JETBOT_PORT,
    host="0.0.0.0",
    camera_width=224,
    camera_height=224,
):
    """
    Start Jetbot RPyC server.

    Args:
        port: Port to listen on (default: 18861)
        host: Host address to bind to (default: 0.0.0.0 for all interfaces)
        camera_width: Camera frame width (default: 224)
        camera_height: Camera frame height (default: 224)
    """
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    logger.info("=" * 60)
    logger.info("Starting Jetbot RPyC Server")
    logger.info("=" * 60)
    logger.info("Host: {}".format(host))
    logger.info("Port: {}".format(port))
    logger.info("Camera: {}x{}".format(camera_width, camera_height))
    logger.info("=" * 60)

    # Create service
    service = JetbotService(camera_width=camera_width, camera_height=camera_height)

    # Create RPyC server
    server = ThreadedServer(
        service,
        port=port,
        hostname=host,
        protocol_config={
            'allow_all_attrs': True,
            'allow_pickle': True,
            'allow_public_attrs': True,
            'sync_request_timeout': 30,
        }
    )

    try:
        logger.info("Server started successfully")
        logger.info("Clients can connect to {}:{}".format(host, port))
        logger.info("Press Ctrl+C to stop server")
        server.start()
    except KeyboardInterrupt:
        logger.info("\nServer interrupted by user")
    except Exception as e:
        logger.error("Server error: {}".format(e))
        raise
    finally:
        logger.info("Shutting down Jetbot server")


if __name__ == "__main__":
    start_jetbot_server()
