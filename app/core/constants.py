"""Centralized status and role constants.

Python 3.9 compatible: uses constant classes + Literal type aliases
instead of StrEnum (Python 3.11+).
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


class UserRole:
    ADMIN = "admin"
    USER = "user"


UserRoleType = Literal["admin", "user"]
