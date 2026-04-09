"""
Logging configuration for the package.
"""

import logging
from pathlib import Path

logger = logging.getLogger('ng_rdm')
logger.addHandler(logging.NullHandler())

_FORMAT = "%(asctime)s - %(module)s - %(funcName)s - line:%(lineno)d - %(levelname)s - %(message)s"


def _configure_file_logging(log_file: str | Path) -> None:
    """Route ng_rdm, Tortoise ORM, and uvicorn logs to a file. Called by rdm_init()."""
    if any(isinstance(h, logging.FileHandler) for h in logger.handlers):
        return
    handler = logging.FileHandler(filename=log_file)
    handler.setFormatter(logging.Formatter(_FORMAT))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False
    for name in ("tortoise", "uvicorn"):
        third = logging.getLogger(name)
        third.setLevel(logging.ERROR)
        third.addHandler(handler)
    logger.info("Logging to %s initialized", log_file)
