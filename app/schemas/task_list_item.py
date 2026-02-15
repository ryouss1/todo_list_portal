from datetime import date, datetime
from typing import Literal, Optional

from pydantic import BaseModel


class TaskListItemCreate(BaseModel):
    title: str
    description: Optional[str] = None
    scheduled_date: Optional[date] = None
    category_id: Optional[int] = None
    backlog_ticket_id: Optional[str] = None
    assignee_id: Optional[int] = None


class TaskListItemUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    scheduled_date: Optional[date] = None
    category_id: Optional[int] = None
    backlog_ticket_id: Optional[str] = None
    status: Optional[Literal["open", "in_progress", "done"]] = None


class TaskListItemResponse(BaseModel):
    id: int
    title: str
    description: Optional[str] = None
    scheduled_date: Optional[date] = None
    assignee_id: Optional[int] = None
    created_by: int
    status: str
    total_seconds: int
    category_id: Optional[int] = None
    backlog_ticket_id: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}
