"""App-specific status and type constants.

Python 3.9 compatible: uses constant classes + Literal type aliases
instead of StrEnum (Python 3.11+).

Core constants (UserRole) remain in app/core/constants.py.
"""

from typing import Literal


class TaskStatus:
    PENDING = "pending"
    IN_PROGRESS = "in_progress"


TaskStatusType = Literal["pending", "in_progress"]


class ItemStatus:
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    DONE = "done"


ItemStatusType = Literal["open", "in_progress", "done"]


class PresenceStatusValue:
    AVAILABLE = "available"
    AWAY = "away"
    OUT = "out"
    BREAK = "break"
    OFFLINE = "offline"
    MEETING = "meeting"
    REMOTE = "remote"


PresenceStatusType = Literal["available", "away", "out", "break", "offline", "meeting", "remote"]


class InputType:
    WEB = "web"
    IC_CARD = "ic_card"
    ADMIN = "admin"


InputTypeValue = Literal["web", "ic_card", "admin"]


class AlertSeverity:
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


AlertSeverityType = Literal["info", "warning", "critical"]


class WikiPageVisibility:
    LOCAL = "local"  # 自部署（同一グループのユーザーのみ）
    PUBLIC = "public"  # 他部署（全ログインユーザー、旧 internal）
    PRIVATE = "private"  # 非公開（作成者のみ）


WikiPageVisibilityType = Literal["local", "public", "private"]


class AccessMethod:
    FTP = "ftp"
    SMB = "smb"


AccessMethodType = Literal["ftp", "smb"]


class SiteLinkStatus:
    UNKNOWN = "unknown"
    UP = "up"
    DOWN = "down"
    ERROR = "error"


SiteLinkStatusType = Literal["unknown", "up", "down", "error"]


class LogFileStatus:
    NEW = "new"
    UNCHANGED = "unchanged"
    UPDATED = "updated"
    DELETED = "deleted"
    ERROR = "error"


LogFileStatusType = Literal["new", "unchanged", "updated", "deleted", "error"]


class LogSourceType:
    WEB = "WEB"
    HT = "HT"
    BATCH = "BATCH"
    OTHER = "OTHER"


LogSourceTypeValue = Literal["WEB", "HT", "BATCH", "OTHER"]

# Default log file glob pattern used by LogSourcePath
DEFAULT_LOG_FILE_PATTERN: str = "*.log"
