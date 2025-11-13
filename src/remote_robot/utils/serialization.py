"""
Serialization utilities for efficient data transfer over RPyC.

Handles encoding/decoding of observations, particularly image data.
"""

import base64
import io
from typing import Any

import cv2
import numpy as np


def encode_image(image: np.ndarray, format: str = ".jpg", quality: int = 90) -> str:
    """
    Encode a numpy image array to base64 string.

    Args:
        image: Image as numpy array (HxWxC)
        format: Image format ('.jpg' or '.png')
        quality: JPEG quality (0-100), ignored for PNG

    Returns:
        Base64-encoded image string
    """
    if format == ".jpg":
        encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), quality]
    else:
        encode_param = []

    success, encoded_image = cv2.imencode(format, image, encode_param)
    if not success:
        raise ValueError(f"Failed to encode image to {format}")

    jpg_bytes = encoded_image.tobytes()
    jpg_b64 = base64.b64encode(jpg_bytes).decode('utf-8')
    return jpg_b64


def decode_image(encoded_str: str) -> np.ndarray:
    """
    Decode a base64 image string to numpy array.

    Args:
        encoded_str: Base64-encoded image string

    Returns:
        Image as numpy array (HxWxC) in BGR format
    """
    jpg_bytes = base64.b64decode(encoded_str)
    jpg_array = np.frombuffer(jpg_bytes, dtype=np.uint8)
    image = cv2.imdecode(jpg_array, cv2.IMREAD_COLOR)

    if image is None:
        raise ValueError("Failed to decode image from base64 string")

    return image


def encode_observation(obs: dict[str, Any]) -> dict[str, Any]:
    """
    Encode an observation dictionary for network transfer.

    Images (numpy arrays with 3 dimensions) are encoded to base64 strings.
    Other values are passed through unchanged.

    Args:
        obs: Observation dictionary from robot.get_observation()

    Returns:
        Encoded observation dictionary safe for RPyC transfer
    """
    encoded = {}
    for key, value in obs.items():
        if isinstance(value, np.ndarray):
            if value.ndim == 3:  # Image: (H, W, C)
                encoded[key] = {
                    "__type__": "image",
                    "data": encode_image(value),
                    "shape": value.shape,
                    "dtype": str(value.dtype),
                }
            else:  # Other arrays (scalars, vectors, etc.)
                encoded[key] = {
                    "__type__": "array",
                    "data": value.tolist(),
                    "shape": value.shape,
                    "dtype": str(value.dtype),
                }
        elif isinstance(value, (float, int, bool)):
            encoded[key] = value
        else:
            # Pass through other types
            encoded[key] = value

    return encoded


def decode_observation(encoded: dict[str, Any]) -> dict[str, Any]:
    """
    Decode an encoded observation dictionary.

    Args:
        encoded: Encoded observation from encode_observation()

    Returns:
        Original observation dictionary with numpy arrays restored
    """
    decoded = {}
    for key, value in encoded.items():
        if isinstance(value, dict) and "__type__" in value:
            if value["__type__"] == "image":
                decoded[key] = decode_image(value["data"])
            elif value["__type__"] == "array":
                decoded[key] = np.array(value["data"], dtype=np.dtype(value["dtype"]))
        else:
            decoded[key] = value

    return decoded


def encode_action(action: dict[str, Any]) -> dict[str, Any]:
    """
    Encode an action dictionary for network transfer.

    Converts numpy arrays to lists for JSON serialization.

    Args:
        action: Action dictionary to send to robot

    Returns:
        Encoded action dictionary safe for RPyC transfer
    """
    encoded = {}
    for key, value in action.items():
        if isinstance(value, np.ndarray):
            encoded[key] = value.tolist()
        else:
            encoded[key] = value

    return encoded


def decode_action(encoded: dict[str, Any]) -> dict[str, Any]:
    """
    Decode an encoded action dictionary.

    Args:
        encoded: Encoded action from encode_action()

    Returns:
        Original action dictionary (passes through as-is)
    """
    # Actions are typically simple floats, no decoding needed
    return encoded
