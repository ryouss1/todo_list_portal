"""Portal core schemas."""

from portal_core.schemas.department import (
    DepartmentCreate,
    DepartmentResponse,
    DepartmentUpdate,
)
from portal_core.schemas.menu import MenuCreate, MenuResponse, MenuUpdate
from portal_core.schemas.role import PermissionItem, RoleCreate, RoleResponse, RoleUpdate

__all__ = [
    "DepartmentCreate",
    "DepartmentUpdate",
    "DepartmentResponse",
    "PermissionItem",
    "RoleCreate",
    "RoleUpdate",
    "RoleResponse",
    "MenuCreate",
    "MenuUpdate",
    "MenuResponse",
]
