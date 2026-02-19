import os

from dotenv import load_dotenv

load_dotenv()

DATABASE_URL: str = os.environ.get("DATABASE_URL", "")
DEFAULT_USER_ID: int = int(os.environ.get("DEFAULT_USER_ID", "1"))
DEFAULT_EMAIL: str = os.environ.get("DEFAULT_EMAIL", "admin@example.com")
DEFAULT_DISPLAY_NAME: str = os.environ.get("DEFAULT_DISPLAY_NAME", "Default User")
SECRET_KEY: str = os.environ.get("SECRET_KEY", "")
DEFAULT_PASSWORD: str = os.environ.get("DEFAULT_PASSWORD", "")

# Server
SERVER_HOST: str = os.environ.get("SERVER_HOST", "0.0.0.0")
SERVER_PORT: int = int(os.environ.get("SERVER_PORT", "8000"))
SERVER_RELOAD: bool = os.environ.get("SERVER_RELOAD", "true").lower() == "true"

# Session / Cookie
SESSION_MAX_AGE: int = int(os.environ.get("SESSION_MAX_AGE", "1209600"))  # 14 days
SESSION_COOKIE_SECURE: bool = os.environ.get("SESSION_COOKIE_SECURE", "false").lower() == "true"
SESSION_COOKIE_SAMESITE: str = os.environ.get("SESSION_COOKIE_SAMESITE", "lax")
# Note: Starlette SessionMiddleware always sets HttpOnly=true (not configurable)

# Database connection pool
DB_POOL_SIZE: int = int(os.environ.get("DB_POOL_SIZE", "5"))
DB_MAX_OVERFLOW: int = int(os.environ.get("DB_MAX_OVERFLOW", "10"))
DB_POOL_RECYCLE: int = int(os.environ.get("DB_POOL_RECYCLE", "-1"))
DB_POOL_PRE_PING: bool = os.environ.get("DB_POOL_PRE_PING", "true").lower() == "true"

# Logging
LOG_MAX_BYTES: int = int(os.environ.get("LOG_MAX_BYTES", "10485760"))  # 10 MB
LOG_BACKUP_COUNT: int = int(os.environ.get("LOG_BACKUP_COUNT", "5"))

# Log source polling
LOG_SOURCE_DEFAULT_POLLING_SEC: int = int(os.environ.get("LOG_SOURCE_DEFAULT_POLLING_SEC", "60"))
LOG_SOURCE_MIN_POLLING_SEC: int = int(os.environ.get("LOG_SOURCE_MIN_POLLING_SEC", "60"))
LOG_SOURCE_MAX_POLLING_SEC: int = int(os.environ.get("LOG_SOURCE_MAX_POLLING_SEC", "3600"))

# Log collection v2
CREDENTIAL_ENCRYPTION_KEY: str = os.environ.get("CREDENTIAL_ENCRYPTION_KEY", "")
LOG_FTP_CONNECT_TIMEOUT: int = int(os.environ.get("LOG_FTP_CONNECT_TIMEOUT", "30"))
LOG_FTP_READ_TIMEOUT: int = int(os.environ.get("LOG_FTP_READ_TIMEOUT", "60"))
LOG_SCAN_PATH_TIMEOUT: int = int(os.environ.get("LOG_SCAN_PATH_TIMEOUT", "300"))  # per-path scan timeout (seconds)

# Source type constants
LOG_SOURCE_TYPES: list = ["WEB", "HT", "BATCH", "OTHER"]

# Business logic
MAX_ATTENDANCE_BREAKS: int = int(os.environ.get("MAX_ATTENDANCE_BREAKS", "3"))
DEFAULT_TASK_CATEGORY_ID: int = int(os.environ.get("DEFAULT_TASK_CATEGORY_ID", "7"))

# API default limits
API_LOG_LIMIT: int = int(os.environ.get("API_LOG_LIMIT", "100"))
API_ALERT_LIMIT: int = int(os.environ.get("API_ALERT_LIMIT", "100"))
API_PRESENCE_LOG_LIMIT: int = int(os.environ.get("API_PRESENCE_LOG_LIMIT", "50"))

# Frontend CDN URLs
BOOTSTRAP_CSS_URL: str = os.environ.get(
    "BOOTSTRAP_CSS_URL", "https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css"
)
BOOTSTRAP_ICONS_URL: str = os.environ.get(
    "BOOTSTRAP_ICONS_URL", "https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.min.css"
)
BOOTSTRAP_JS_URL: str = os.environ.get(
    "BOOTSTRAP_JS_URL", "https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js"
)

FULLCALENDAR_JS_URL: str = os.environ.get(
    "FULLCALENDAR_JS_URL", "https://cdn.jsdelivr.net/npm/fullcalendar@6.1.15/index.global.min.js"
)

BACKLOG_SPACE: str = os.environ.get("BACKLOG_SPACE", "ottsystems")

# Password policy
PASSWORD_MIN_LENGTH: int = int(os.environ.get("PASSWORD_MIN_LENGTH", "8"))
PASSWORD_MAX_LENGTH: int = int(os.environ.get("PASSWORD_MAX_LENGTH", "128"))
PASSWORD_REQUIRE_UPPERCASE: bool = os.environ.get("PASSWORD_REQUIRE_UPPERCASE", "true").lower() == "true"
PASSWORD_REQUIRE_LOWERCASE: bool = os.environ.get("PASSWORD_REQUIRE_LOWERCASE", "true").lower() == "true"
PASSWORD_REQUIRE_DIGIT: bool = os.environ.get("PASSWORD_REQUIRE_DIGIT", "true").lower() == "true"
PASSWORD_REQUIRE_SPECIAL: bool = os.environ.get("PASSWORD_REQUIRE_SPECIAL", "false").lower() == "true"

# Rate limiting / Account lockout
LOGIN_MAX_ATTEMPTS: int = int(os.environ.get("LOGIN_MAX_ATTEMPTS", "5"))
LOGIN_RATE_LIMIT_WINDOW_MINUTES: int = int(os.environ.get("LOGIN_RATE_LIMIT_WINDOW_MINUTES", "15"))
ACCOUNT_LOCKOUT_MINUTES: int = int(os.environ.get("ACCOUNT_LOCKOUT_MINUTES", "30"))

# OAuth
OAUTH_STATE_EXPIRY_SECONDS: int = int(os.environ.get("OAUTH_STATE_EXPIRY_SECONDS", "300"))
OAUTH_CALLBACK_BASE_URL: str = os.environ.get("OAUTH_CALLBACK_BASE_URL", "http://localhost:8000")

# Password Reset
PASSWORD_RESET_EXPIRY_MINUTES: int = int(os.environ.get("PASSWORD_RESET_EXPIRY_MINUTES", "30"))
PASSWORD_RESET_COOLDOWN_MINUTES: int = int(os.environ.get("PASSWORD_RESET_COOLDOWN_MINUTES", "15"))
PASSWORD_RESET_MAX_REQUESTS: int = int(os.environ.get("PASSWORD_RESET_MAX_REQUESTS", "3"))
PASSWORD_RESET_BASE_URL: str = os.environ.get("PASSWORD_RESET_BASE_URL", "http://localhost:8000")

# SMTP
SMTP_HOST: str = os.environ.get("SMTP_HOST", "")
SMTP_PORT: int = int(os.environ.get("SMTP_PORT", "587"))
SMTP_USERNAME: str = os.environ.get("SMTP_USERNAME", "")
SMTP_PASSWORD: str = os.environ.get("SMTP_PASSWORD", "")
SMTP_FROM_ADDRESS: str = os.environ.get("SMTP_FROM_ADDRESS", "noreply@example.com")
SMTP_USE_TLS: bool = os.environ.get("SMTP_USE_TLS", "true").lower() == "true"
SMTP_USE_SSL: bool = os.environ.get("SMTP_USE_SSL", "false").lower() == "true"

# Calendar
CALENDAR_REMINDER_ENABLED: bool = os.environ.get("CALENDAR_REMINDER_ENABLED", "true").lower() == "true"
CALENDAR_REMINDER_INTERVAL: int = int(os.environ.get("CALENDAR_REMINDER_INTERVAL", "60"))

# Log scanner (background)
LOG_SCANNER_ENABLED: bool = os.environ.get("LOG_SCANNER_ENABLED", "false").lower() == "true"
LOG_SCANNER_LOOP_INTERVAL: int = int(os.environ.get("LOG_SCANNER_LOOP_INTERVAL", "30"))

# Log alert content reading
LOG_ALERT_CONTENT_MAX_LINES: int = int(os.environ.get("LOG_ALERT_CONTENT_MAX_LINES", "200"))

# i18n
DEFAULT_LOCALE: str = os.environ.get("DEFAULT_LOCALE", "ja")
SUPPORTED_LOCALES: list = ["ja", "en"]
