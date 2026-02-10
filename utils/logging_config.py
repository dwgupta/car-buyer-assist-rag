"""
Logging configuration for Car Buyer Assist RAG application.

Configures format, level, and handlers for consistent logging across the app.
Supports LOG_LEVEL env var (DEBUG, INFO, WARNING, ERROR).
"""

import logging
import os
import sys


def setup_logging(
    level: int | None = None,
    format_string: str | None = None,
) -> None:
    """
    Configure application-wide logging.

    Args:
        level: Logging level. Defaults to INFO, or LOG_LEVEL env var.
        format_string: Custom format. Defaults to timestamp, name, level, message.
    """
    if level is None:
        level = getattr(
            logging,
            os.getenv("LOG_LEVEL", "INFO").upper(),
            logging.INFO,
        )
    if format_string is None:
        format_string = "%(asctime)s | %(name)s | %(levelname)s | %(message)s"

    logging.basicConfig(
        level=level,
        format=format_string,
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[logging.StreamHandler(sys.stdout)],
        force=True,
    )
