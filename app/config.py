import os

from portal_core.config import CoreConfig  # noqa: F401


class AppConfig(CoreConfig):
    """App-specific settings — not shared with portal_core.

    Contains: log source polling, log collection, business logic, API limits,
    calendar, background services, Backlog integration.
    """

    # Log source polling
    LOG_SOURCE_DEFAULT_POLLING_SEC: int = int(os.environ.get("LOG_SOURCE_DEFAULT_POLLING_SEC", "60"))
    LOG_SOURCE_MIN_POLLING_SEC: int = int(os.environ.get("LOG_SOURCE_MIN_POLLING_SEC", "60"))
    LOG_SOURCE_MAX_POLLING_SEC: int = int(os.environ.get("LOG_SOURCE_MAX_POLLING_SEC", "3600"))

    # Log collection v2
    LOG_FTP_CONNECT_TIMEOUT: int = int(os.environ.get("LOG_FTP_CONNECT_TIMEOUT", "30"))
    LOG_FTP_READ_TIMEOUT: int = int(os.environ.get("LOG_FTP_READ_TIMEOUT", "60"))
    LOG_SCAN_PATH_TIMEOUT: int = int(os.environ.get("LOG_SCAN_PATH_TIMEOUT", "300"))  # per-path scan timeout (seconds)

    # Business logic
    MAX_ATTENDANCE_BREAKS: int = int(os.environ.get("MAX_ATTENDANCE_BREAKS", "3"))
    DEFAULT_TASK_CATEGORY_ID: int = int(os.environ.get("DEFAULT_TASK_CATEGORY_ID", "7"))

    # API default limits
    API_LOG_LIMIT: int = int(os.environ.get("API_LOG_LIMIT", "100"))
    API_ALERT_LIMIT: int = int(os.environ.get("API_ALERT_LIMIT", "100"))
    API_PRESENCE_LOG_LIMIT: int = int(os.environ.get("API_PRESENCE_LOG_LIMIT", "50"))
    PRESENCE_ACTIVE_TASK_LIMIT: int = int(os.environ.get("PRESENCE_ACTIVE_TASK_LIMIT", "200"))

    # FullCalendar
    FULLCALENDAR_JS_URL: str = os.environ.get(
        "FULLCALENDAR_JS_URL", "https://cdn.jsdelivr.net/npm/fullcalendar@6.1.15/index.global.min.js"
    )

    # Backlog integration
    BACKLOG_SPACE: str = os.environ.get("BACKLOG_SPACE", "ottsystems")

    # Calendar
    CALENDAR_REMINDER_ENABLED: bool = os.environ.get("CALENDAR_REMINDER_ENABLED", "true").lower() == "true"
    CALENDAR_REMINDER_INTERVAL: int = int(os.environ.get("CALENDAR_REMINDER_INTERVAL", "60"))
    CALENDAR_REMINDER_STALE_MINUTES: int = int(os.environ.get("CALENDAR_REMINDER_STALE_MINUTES", "10"))

    # Log scanner (background)
    LOG_SCANNER_ENABLED: bool = os.environ.get("LOG_SCANNER_ENABLED", "false").lower() == "true"
    LOG_SCANNER_LOOP_INTERVAL: int = int(os.environ.get("LOG_SCANNER_LOOP_INTERVAL", "30"))
    LOG_SOURCE_MAX_CONSECUTIVE_FAILURES: int = int(os.environ.get("LOG_SOURCE_MAX_CONSECUTIVE_FAILURES", "5"))
    LOG_SCANNER_STALE_MINUTES: int = int(os.environ.get("LOG_SCANNER_STALE_MINUTES", "10"))

    # Site checker (background)
    SITE_CHECKER_ENABLED: bool = os.environ.get("SITE_CHECKER_ENABLED", "false").lower() == "true"
    SITE_CHECKER_LOOP_INTERVAL: int = int(os.environ.get("SITE_CHECKER_LOOP_INTERVAL", "60"))
    SITE_CHECK_MAX_REDIRECTS: int = int(os.environ.get("SITE_CHECK_MAX_REDIRECTS", "5"))
    SITE_MAX_CONSECUTIVE_FAILURES: int = int(os.environ.get("SITE_MAX_CONSECUTIVE_FAILURES", "5"))
    SITE_CHECKER_STALE_MINUTES: int = int(os.environ.get("SITE_CHECKER_STALE_MINUTES", "10"))

    # Log alert content reading
    LOG_ALERT_CONTENT_MAX_LINES: int = int(os.environ.get("LOG_ALERT_CONTENT_MAX_LINES", "200"))
    LOG_ALERT_CONTENT_DISPLAY_LINES: int = int(os.environ.get("LOG_ALERT_CONTENT_DISPLAY_LINES", "50"))


# Backward compatibility: expose all config as module-level variables.
# Existing `from app.config import X` continues to work unchanged.
for _name in dir(AppConfig):
    if _name.isupper() and not _name.startswith("_"):
        globals()[_name] = getattr(AppConfig, _name)
