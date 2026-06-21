"""
Centralized logging configuration using loguru.

Import `get_logger(__name__)` anywhere in the app to get a consistently
configured logger instead of using `print()`.
"""

import sys

from loguru import logger

_CONFIGURED = False


def _configure_once() -> None:
    global _CONFIGURED
    if _CONFIGURED:
        return

    logger.remove()  # drop default handler
    logger.add(
        sys.stderr,
        level="INFO",
        colorize=True,
        format=(
            "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{extra[component]}</cyan> | "
            "<level>{message}</level>"
        ),
    )
    _CONFIGURED = True


def get_logger(component: str):
    """Return a logger bound with a component name for readable logs."""
    _configure_once()
    return logger.bind(component=component)
