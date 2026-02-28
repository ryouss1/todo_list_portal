import os

from portal_core.config import LOG_BACKUP_COUNT, LOG_DIR, LOG_MAX_BYTES, SQL_LOG_LEVEL

LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")

# Ensure log directory exists on import
os.makedirs(LOG_DIR, exist_ok=True)


def _log_path(name: str) -> str:
    return os.path.join(LOG_DIR, name)


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
        "app_file": {
            "class": "logging.handlers.RotatingFileHandler",
            "formatter": "default",
            "filename": _log_path("app.log"),
            "maxBytes": LOG_MAX_BYTES,
            "backupCount": LOG_BACKUP_COUNT,
            "encoding": "utf-8",
        },
        "sql_file": {
            "class": "logging.handlers.RotatingFileHandler",
            "formatter": "default",
            "filename": _log_path("sql.log"),
            "maxBytes": LOG_MAX_BYTES,
            "backupCount": LOG_BACKUP_COUNT,
            "encoding": "utf-8",
        },
        "error_file": {
            "class": "logging.handlers.RotatingFileHandler",
            "formatter": "default",
            "level": "ERROR",
            "filename": _log_path("error.log"),
            "maxBytes": LOG_MAX_BYTES,
            "backupCount": LOG_BACKUP_COUNT,
            "encoding": "utf-8",
        },
    },
    "loggers": {
        "app": {
            "level": LOG_LEVEL,
            "handlers": ["console", "app_file", "error_file"],
            "propagate": False,
        },
        "portal_core": {
            "level": LOG_LEVEL,
            "handlers": ["console", "app_file", "error_file"],
            "propagate": False,
        },
        "sqlalchemy.engine": {
            "level": SQL_LOG_LEVEL,
            "handlers": ["sql_file"],
            "propagate": False,
        },
        "sqlalchemy.pool": {
            "level": SQL_LOG_LEVEL,
            "handlers": ["sql_file"],
            "propagate": False,
        },
        "watchfiles": {  # "N changes detected" スパム抑制
            "level": "WARNING",
            "handlers": ["console"],
            "propagate": False,
        },
    },
    "root": {
        "level": LOG_LEVEL,
        "handlers": ["console", "app_file", "error_file"],
    },
}
