"""
Logging configuration for the package.
"""

import logging
from pathlib import Path

logger = logging.getLogger('ng_rdm')
logger.addHandler(logging.NullHandler())

_FORMAT = "%(asctime)s - %(module)s - %(funcName)s - line:%(lineno)d - %(levelname)s - %(message)s"


def configure_logging(
    log_file: str | Path | None = None,
    level: int | str = logging.INFO,
    console: bool = False,
    tortoise_level: int | str = logging.ERROR,
    uvicorn_level: int | str = logging.ERROR,
) -> None:
    """Configure ng_rdm logging. Call once from main.py before any startup code.

    Without arguments, this is a no-op — the library stays silent and logs propagate
    to the root logger if the host app configures one.

    Args:
        log_file: Optional path. When set, logs are written to this file.
        level: Log level for the ng_rdm logger (default: INFO).
        console: If True, also emit to stderr.
        tortoise_level: Log level for Tortoise ORM loggers (default: ERROR).
        uvicorn_level: Log level for uvicorn loggers (default: ERROR).
    """
    if not log_file and not console:
        return

    formatter = logging.Formatter(_FORMAT)
    handlers: list[logging.Handler] = []

    if log_file:
        # Guard against duplicate FileHandlers on repeated calls
        if not any(isinstance(h, logging.FileHandler) for h in logger.handlers):
            handlers.append(logging.FileHandler(filename=log_file))

    if console:
        if not any(isinstance(h, logging.StreamHandler) and not isinstance(h, logging.FileHandler)
                   for h in logger.handlers):
            handlers.append(logging.StreamHandler())

    for handler in handlers:
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    if handlers:
        logger.setLevel(level)
        logger.propagate = False
        for name, lvl in (("tortoise", tortoise_level), ("uvicorn", uvicorn_level)):
            third = logging.getLogger(name)
            third.setLevel(lvl)
            for handler in handlers:
                third.addHandler(handler)
        logger.info("Logging initialized (file=%s, console=%s)", log_file, console)
