from functools import lru_cache
import os
import sys

from loguru import logger


@lru_cache()
def setup_logging(
    level=None, file=None, diagnose=False, backtrace=False, time=False
):
    """Configure logging behaviour.

    Parameters
    ----------
    level
        The logging level to use. Default is "INFO".
    file:
        A file where logs should be persisted in addition to being printed to stderr.
    diagnose
        Include diagnostic information. Could leak sensitive information.
    backtrace
        Include full stack traces. Could leak sensitive information.
    """
    format = ""
    if time:
        format += "<green>{time:YYYY-MM-DD HH:mm:ss Z}</green> | "

    format += "<level>{level: <4}</level> | <level>{message}</level>"

    level = level or os.getenv("MODOS_LOG_LEVEL", "INFO").upper()

    logger.remove()  # Remove default handler
    logger.add(
        sys.stderr,
        level=level,
        format=format,
        backtrace=backtrace,
        diagnose=diagnose,
    )

    if file:
        logger.add(
            file,
            level=level,
            format=format,
            backtrace=backtrace,
            diagnose=diagnose,
            rotation="10 MB",
            retention="10 days",
        )
