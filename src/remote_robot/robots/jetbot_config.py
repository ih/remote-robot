"""
Jetbot robot configuration compatible with LeRobot 0.4.2+ API.
"""

from dataclasses import dataclass, field

from lerobot.cameras.configs import CameraConfig
from lerobot.robots.utils import RobotConfig


@RobotConfig.register_subclass("jetbot")
@dataclass
class JetbotConfig(RobotConfig):
    """
    Configuration for Jetbot differential drive robot.

    Compatible with LeRobot 0.4.2+ RobotConfig pattern using draccus.ChoiceRegistry.

    Uses jetbot.Robot with default hardware configuration.
    For custom motor channels or calibration, modify jetbot package config directly.
    """

    # Robot operation mode
    mock: bool = False  # If True, use mock hardware for testing

    # Motor control
    disable_motors_on_disconnect: bool = True  # Stop motors when disconnecting

    # Cameras configuration (LeRobot standard)
    cameras: dict[str, CameraConfig] = field(default_factory=dict)
