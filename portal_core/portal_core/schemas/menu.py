from datetime import datetime
from typing import Optional

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
