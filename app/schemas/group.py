from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class GroupCreate(BaseModel):
    name: str
    description: Optional[str] = None
    sort_order: int = 0


class GroupUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    sort_order: Optional[int] = None


class GroupResponse(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    sort_order: int
    member_count: int = 0
    created_at: datetime

    model_config = {"from_attributes": True}
