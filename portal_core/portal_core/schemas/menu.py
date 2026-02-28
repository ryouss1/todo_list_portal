from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel


class MenuCreate(BaseModel):
    name: str
    label: str
    path: str
    icon: str = ""
    badge_id: Optional[str] = None
    parent_id: Optional[int] = None
    sort_order: int = 100
    required_resource: Optional[str] = None
    required_action: Optional[str] = None


class MenuUpdate(BaseModel):
    label: Optional[str] = None
    path: Optional[str] = None
    icon: Optional[str] = None
    badge_id: Optional[str] = None
    parent_id: Optional[int] = None
    sort_order: Optional[int] = None
    is_active: Optional[bool] = None
    required_resource: Optional[str] = None
    required_action: Optional[str] = None


class MenuResponse(BaseModel):
    id: int
    name: str
    label: str
    path: str
    icon: str
    badge_id: Optional[str] = None
    parent_id: Optional[int] = None
    sort_order: int
    is_active: bool
    required_resource: Optional[str] = None
    required_action: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class VisibilityItem(BaseModel):
    """Single ON/OFF entry in a batch visibility update."""

    id: int  # role_id / department_id / user_id depending on context
    kino_kbn: int  # 1=show, 0=hide


class RoleVisibilityEntry(BaseModel):
    role_id: int
    menu_id: int
    kino_kbn: int

    model_config = {"from_attributes": True}


class DepartmentVisibilityEntry(BaseModel):
    department_id: int
    menu_id: int
    kino_kbn: int

    model_config = {"from_attributes": True}


class UserVisibilityEntry(BaseModel):
    user_id: int
    menu_id: int
    kino_kbn: int

    model_config = {"from_attributes": True}


class VisibilityBatchUpdate(BaseModel):
    """Request body for batch visibility PUT endpoints."""

    items: List[VisibilityItem]


class MyVisibilityEntry(BaseModel):
    menu_id: int
    kino_kbn: int

    model_config = {"from_attributes": True}


class MyVisibilityUpdate(BaseModel):
    """Request body for self-service visibility update."""

    menu_id: int
    kino_kbn: int  # 1=show, 0=hide


class MyVisibilityReset(BaseModel):
    """Request body for self-service visibility reset."""

    menu_id: int
