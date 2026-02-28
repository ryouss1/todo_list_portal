from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel


class PermissionItem(BaseModel):
    resource: str
    action: str
    kino_kbn: int = 1


class RoleCreate(BaseModel):
    name: str
    display_name: str
    description: Optional[str] = None
    sort_order: int = 0


class RoleUpdate(BaseModel):
    display_name: Optional[str] = None
    description: Optional[str] = None
    sort_order: Optional[int] = None
    is_active: Optional[bool] = None


class RoleResponse(BaseModel):
    id: int
    name: str
    display_name: str
    description: Optional[str] = None
    sort_order: int
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None
    permissions: List[PermissionItem] = []

    model_config = {"from_attributes": True}
