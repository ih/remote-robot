"""
remote_robot - LeRobot-compatible robot control package

Provides remote and local control for Jetbot and SO-101 robots with full
LeRobot API compatibility.
"""

from remote_robot.robots.jetbot_config import JetbotConfig
from remote_robot.robots.jetbot_remote import JetbotRemote
from remote_robot.robots.so101_remote import SO101Remote

__version__ = "0.1.0"
__all__ = ["JetbotRemote", "JetbotConfig", "SO101Remote"]
