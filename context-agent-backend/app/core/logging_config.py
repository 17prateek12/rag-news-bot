import logging
import sys
from logging.config import dictConfig

from app.config import settings

LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def setup_logging() -> None:
    level = getattr(logging, settings.log_level.upper(), logging.INFO)

    dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "default": {
                    "format": LOG_FORMAT,
                    "datefmt": LOG_DATE_FORMAT,
                },
            },
            "handlers": {
                "console": {
                    "class": "logging.StreamHandler",
                    "formatter": "default",
                    "stream": "ext://sys.stdout",
                },
            },
            "root": {
                "level": level,
                "handlers": ["console"],
            },
            "loggers": {
                "app": {"level": level, "propagate": True},
                "uvicorn": {"level": level, "propagate": True},
                "uvicorn.error": {"level": level, "propagate": True},
                "uvicorn.access": {"level": level, "propagate": True},
                "alembic": {"level": level, "propagate": True},
                "httpx": {"level": "WARNING", "propagate": True},
                "httpcore": {"level": "WARNING", "propagate": True},
            },
        }
    )

    # Force unbuffered output on Windows terminals.
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(line_buffering=True)
        except Exception:
            pass


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
