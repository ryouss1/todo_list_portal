from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel


class DailyReportCreate(BaseModel):
    report_date: date
    category_id: int
    task_name: str
    backlog_ticket_id: Optional[str] = None
    time_minutes: int = 0
    work_content: str
    achievements: Optional[str] = None
    issues: Optional[str] = None
    next_plan: Optional[str] = None
    remarks: Optional[str] = None


class DailyReportUpdate(BaseModel):
    category_id: Optional[int] = None
    task_name: Optional[str] = None
    backlog_ticket_id: Optional[str] = None
    time_minutes: Optional[int] = None
    work_content: Optional[str] = None
    achievements: Optional[str] = None
    issues: Optional[str] = None
    next_plan: Optional[str] = None
    remarks: Optional[str] = None


class DailyReportResponse(BaseModel):
    id: int
    user_id: int
    report_date: date
    category_id: int
    task_name: str
    backlog_ticket_id: Optional[str] = None
    time_minutes: int
    work_content: str
    achievements: Optional[str] = None
    issues: Optional[str] = None
    next_plan: Optional[str] = None
    remarks: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}
