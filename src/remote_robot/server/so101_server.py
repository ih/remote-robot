"""
RPyC server for SO-101 robot arm.

Run this script on the computer connected to SO-101 hardware to enable remote control.
"""

import logging

from lerobot.robots.so101_follower import SO101Follower, SO101FollowerConfig
from remote_robot.server.base import BaseRobotServer


logger = logging.getLogger(__name__)

DEFAULT_SO101_PORT = 18862


class SO101Server(BaseRobotServer):
    """
    RPyC server for SO-101 robot arm.

    Exposes SO-101 robot via RPyC for remote control.
    Uses LeRobot's SO101Follower with full API compatibility.
    """

    def __init__(self, config: SO101FollowerConfig):
        """
        Initialize SO-101 server.

        Args:
            config: SO101FollowerConfig for robot configuration
        """
        super().__init__()
        self.config = config
        self.logger.info(f"SO101Server initialized with config: {config}")

    def _initialize_robot(self):
        """Initialize SO-101 hardware."""
        self.logger.info("Initializing SO-101 robot")
        self._robot = SO101Follower(self.config)
        self.logger.info("SO-101 robot initialized")

    def _cleanup_robot(self):
        """Clean up SO-101 hardware - disable torque and disconnect."""
        if self._robot is not None:
            try:
                if self._robot.is_connected:
                    self.logger.info("Disconnecting SO-101")
                    self._robot.disconnect()
                    self.logger.info("SO-101 cleaned up successfully")
            except Exception as e:
                self.logger.error(f"Error cleaning up SO-101: {e}")
            finally:
                self._robot = None


def start_so101_server(
    config: SO101FollowerConfig,
    port: int = DEFAULT_SO101_PORT,
    host: str = "0.0.0.0",
):
    """
    Start SO-101 RPyC server.

    Args:
        config: SO101FollowerConfig for robot
        port: Port to listen on (default: 18862)
        host: Host address to bind to (default: 0.0.0.0 for all interfaces)
    """
    import rpyc
    from rpyc.utils.server import ThreadedServer

    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    logger.info(f"Starting SO-101 RPyC server on {host}:{port}")
    logger.info(f"Config: {config}")

    # Create server
    service = SO101Server(config)

    # RPyC server configuration
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
        logger.info("SO-101 server started successfully")
        logger.info(f"Clients can connect to {host}:{port}")
        server.start()
    except KeyboardInterrupt:
        logger.info("Server interrupted by user")
    except Exception as e:
        logger.error(f"Server error: {e}")
        raise
    finally:
        logger.info("Shutting down SO-101 server")
