"""
Remote client utilities for establishing RPyC connections.
"""

import logging
import time
from typing import Optional

import rpyc
from rpyc.core.protocol import Connection


logger = logging.getLogger(__name__)


class RemoteConnectionError(Exception):
    """Raised when unable to establish remote connection."""
    pass


def create_rpyc_connection(
    host: str,
    port: int,
    timeout: int = 30,
    retry_attempts: int = 3,
    retry_delay: float = 1.0,
    config: Optional[dict] = None,
) -> Connection:
    """
    Create an RPyC connection with retry logic.

    Args:
        host: Remote host address (IP or hostname)
        port: Remote port number
        timeout: Connection timeout in seconds
        retry_attempts: Number of connection attempts
        retry_delay: Delay between retry attempts in seconds
        config: Optional RPyC configuration dict

    Returns:
        RPyC connection object

    Raises:
        RemoteConnectionError: If connection cannot be established
    """
    if config is None:
        config = {
            'allow_all_attrs': True,
            'sync_request_timeout': timeout,
            'allow_pickle': True,
        }

    last_error = None
    for attempt in range(1, retry_attempts + 1):
        try:
            logger.info(f"Attempting to connect to {host}:{port} (attempt {attempt}/{retry_attempts})")
            conn = rpyc.connect(host, port, config=config)
            logger.info(f"Successfully connected to {host}:{port}")
            return conn

        except (ConnectionRefusedError, TimeoutError, OSError) as e:
            last_error = e
            logger.warning(f"Connection attempt {attempt} failed: {e}")

            if attempt < retry_attempts:
                logger.info(f"Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
            else:
                logger.error(f"All {retry_attempts} connection attempts failed")

    raise RemoteConnectionError(
        f"Failed to connect to {host}:{port} after {retry_attempts} attempts. "
        f"Last error: {last_error}"
    )


def test_connection(conn: Connection) -> bool:
    """
    Test if an RPyC connection is alive and responsive.

    Args:
        conn: RPyC connection to test

    Returns:
        True if connection is alive, False otherwise
    """
    try:
        # Try to access the root object
        _ = conn.root
        return True
    except Exception as e:
        logger.debug(f"Connection test failed: {e}")
        return False
