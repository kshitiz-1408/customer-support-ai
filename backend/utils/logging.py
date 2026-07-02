import logging
import sys
from config.config import settings


def setup_logging():
    """
    Setup logging configuration for the FastAPI application.
    """
    log_level = logging.DEBUG if settings.DEBUG else logging.INFO

    # Define standard format
    log_format = (
        "[%(asctime)s] %(levelname)s in %(module)s [%(pathname)s:%(lineno)d]:\n"
        "%(message)s\n"
        "--------------------------------------------------------------------------------"
    )

    logging.basicConfig(
        level=log_level,
        format=log_format,
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )

    logger = logging.getLogger("customer_support_backend")
    logger.info(f"Logging initialized with level: {logging.getLevelName(log_level)}")
    return logger


logger = setup_logging()
