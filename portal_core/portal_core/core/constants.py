"""Core constants shared with portal_core.

Python 3.9 compatible: uses constant classes + Literal type aliases
instead of StrEnum (Python 3.11+).

App-specific constants (TaskStatus, ItemStatus, etc.) are in app/constants.py.
"""

from typing import Literal


class UserRole:
    ADMIN = "admin"
    USER = "user"


UserRoleType = Literal["admin", "user"]
