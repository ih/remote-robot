"""Utility functions for remote robot control."""

from remote_robot.utils.serialization import (
    encode_image,
    decode_image,
    encode_observation,
    decode_observation,
    encode_action,
    decode_action,
)
from remote_robot.utils.remote_client import (
    create_rpyc_connection,
    test_connection,
    RemoteConnectionError,
)


# Exception classes for device connection management
class DeviceAlreadyConnectedError(Exception):
    """Raised when attempting to connect to an already connected device."""
    pass


class DeviceNotConnectedError(Exception):
    """Raised when attempting to use a device that is not connected."""
    pass


__all__ = [
    "encode_image",
    "decode_image",
    "encode_observation",
    "decode_observation",
    "encode_action",
    "decode_action",
    "create_rpyc_connection",
    "test_connection",
    "RemoteConnectionError",
    "DeviceAlreadyConnectedError",
    "DeviceNotConnectedError",
]
