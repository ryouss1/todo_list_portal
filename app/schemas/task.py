from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel


class TaskBase(BaseModel):
    title: str
    description: Optional[str] = None
    report: bool = False
    category_id: Optional[int] = None
    backlog_ticket_id: Optional[str] = None


class TaskCreate(TaskBase):
    pass


class TaskUpdate(TaskBase):
    title: Optional[str] = None
    report: Optional[bool] = None
    category_id: Optional[int] = None
    backlog_ticket_id: Optional[str] = None


class TimeEntryResponse(BaseModel):
    id: int
    task_id: int
    started_at: datetime
    stopped_at: Optional[datetime] = None
    elapsed_seconds: int
    created_at: datetime

    model_config = {"from_attributes": True}


class TaskResponse(TaskBase):
    id: int
    user_id: int
    status: str
    total_seconds: int
    report: bool
    category_id: Optional[int] = None
    backlog_ticket_id: Optional[str] = None
    source_item_id: Optional[int] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class BatchDoneItem(BaseModel):
    task_id: int
    end_time: str  # "HH:MM"


class BatchDoneRequest(BaseModel):
    tasks: List[BatchDoneItem]


class BatchDoneResult(BaseModel):
    task_id: int
    report_id: Optional[int] = None


class BatchDoneResponse(BaseModel):
    results: List[BatchDoneResult]
