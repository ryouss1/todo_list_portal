"""Portal core schemas."""

from portal_core.schemas.department import (
    DepartmentCreate,
    DepartmentResponse,
    DepartmentUpdate,
)
from portal_core.schemas.group import (
    GroupCreate,
    GroupResponse,
    GroupUpdate,
)

__all__ = [
    "DepartmentCreate",
    "DepartmentUpdate",
    "DepartmentResponse",
    "GroupCreate",
    "GroupUpdate",
    "GroupResponse",
]
