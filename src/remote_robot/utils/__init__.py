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
]
