import os

from app.config import LOG_BACKUP_COUNT, LOG_MAX_BYTES

LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")

LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "default": {
            "format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            "datefmt": "%Y-%m-%d %H:%M:%S",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "default",
            "stream": "ext://sys.stdout",
        },
        "file": {
            "class": "logging.handlers.RotatingFileHandler",
            "formatter": "default",
            "filename": os.environ.get("LOG_FILE", "app.log"),
            "maxBytes": LOG_MAX_BYTES,
            "backupCount": LOG_BACKUP_COUNT,
            "encoding": "utf-8",
        },
    },
    "loggers": {
        "app": {
            "level": LOG_LEVEL,
            "handlers": ["console", "file"],
            "propagate": False,
        },
    },
    "root": {
        "level": LOG_LEVEL,
        "handlers": ["console", "file"],
    },
}
