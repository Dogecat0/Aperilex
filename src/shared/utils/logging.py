"""
Logging utilities for the application.
"""

import logging
import sys


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance with standard configuration.

    Args:
        name: Logger name (typically __name__)

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)

    # Avoid double emission when root logging is already configured
    if not logger.handlers:
        root_logger = logging.getLogger()
        if root_logger.handlers:
            return logger

        handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        logger.propagate = False

    return logger
