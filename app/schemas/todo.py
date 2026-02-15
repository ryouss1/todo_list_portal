from datetime import date, datetime
from typing import Literal, Optional

from pydantic import BaseModel


class TodoBase(BaseModel):
    title: str
    description: Optional[str] = None
    priority: int = 0
    due_date: Optional[date] = None
    visibility: Literal["private", "public"] = "private"


class TodoCreate(TodoBase):
    pass


class TodoUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    priority: Optional[int] = None
    due_date: Optional[date] = None
    is_completed: Optional[bool] = None
    visibility: Optional[Literal["private", "public"]] = None


class TodoResponse(TodoBase):
    id: int
    user_id: int
    is_completed: bool
    visibility: str
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}
