"""
Logging configuration for the package.
"""

import logging

# Configure logger
logger = logging.getLogger('ng_loba')

def setup_logging(
    level=logging.INFO,
    log_file=None,
    format_string="%(asctime)s - %(module)s - %(funcName)s - line:%(lineno)d - %(levelname)s - %(message)s",
    enable_console_logging=False,
    tortoise_level=logging.ERROR,
    uvicorn_level=logging.ERROR,
    tortoise_sql_logging=False,
    uvicorn_access_logging=False
):
    """
    Set up logging configuration

    Args:
        level: Logging level for the main logger
        log_file: Path to log file (if None, file logging is disabled)
        format_string: Format string for the log formatter
        enable_console_logging: Whether to enable console logging
        tortoise_level: Logging level for tortoise loggers
        uvicorn_level: Logging level for uvicorn loggers
        tortoise_sql_logging: Whether to enable SQL logging for tortoise
        uvicorn_access_logging: Whether to enable access logging for uvicorn
    """
    # Create formatter
    formatter = logging.Formatter(format_string)

    # Clear existing handlers
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)

    # Add console handler if enabled
    if enable_console_logging:
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

    # Add file handler if log_file is provided
    file_handler = None
    if log_file:
        file_handler = logging.FileHandler(filename=log_file)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    # Set level for main logger
    logger.setLevel(level)

    # Prevent duplicate logging
    logger.propagate = False

    # Configure additional loggers if file_handler exists
    if file_handler:
        # Tortoise ORM logger
        logger_tortoise = logging.getLogger("tortoise")
        logger_tortoise.setLevel(tortoise_level)
        logger_tortoise.addHandler(file_handler)

        # Tortoise SQL logger (for debugging SQL queries)
        if tortoise_sql_logging:
            logger_db_client = logging.getLogger("tortoise.db_client")
            logger_db_client.setLevel(tortoise_level)
            logger_db_client.addHandler(file_handler)

        # Uvicorn logger
        logger_uvicorn = logging.getLogger("uvicorn")
        logger_uvicorn.setLevel(uvicorn_level)
        logger_uvicorn.addHandler(file_handler)

        # Uvicorn access logger
        if uvicorn_access_logging:
            logger_uvicorn_access = logging.getLogger("uvicorn.access")
            logger_uvicorn_access.setLevel(uvicorn_level)
            logger_uvicorn_access.addHandler(file_handler)

        logger.info(f"Logging to {log_file} initialized")

    return logger
