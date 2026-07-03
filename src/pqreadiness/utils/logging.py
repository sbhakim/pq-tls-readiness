"""One place to configure logging for the whole tool."""

from __future__ import annotations

import logging


def setup_logging(level: str = "INFO") -> None:
    """Configure the root logger once, with a simple readable format."""
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s  %(levelname)-7s  %(name)s  %(message)s",
        datefmt="%H:%M:%S",
    )


def get_logger(name: str) -> logging.Logger:
    """Return a namespaced logger (e.g. get_logger(__name__))."""
    return logging.getLogger(name)
