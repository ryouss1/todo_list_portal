from datetime import date, datetime
from typing import List, Optional

from pydantic import BaseModel


class ClockInRequest(BaseModel):
    note: Optional[str] = None


class ClockOutRequest(BaseModel):
    note: Optional[str] = None


class BreakInput(BaseModel):
    start: str  # "HH:MM"
    end: Optional[str] = None  # "HH:MM"


class AttendanceCreate(BaseModel):
    date: date
    clock_in: str  # "HH:MM"
    clock_out: Optional[str] = None
    breaks: Optional[List[BreakInput]] = None
    note: Optional[str] = None


class AttendanceUpdate(BaseModel):
    clock_in: Optional[str] = None
    clock_out: Optional[str] = None
    note: Optional[str] = None
    breaks: Optional[List[BreakInput]] = None


class AttendanceBreakResponse(BaseModel):
    id: int
    break_start: datetime
    break_end: Optional[datetime] = None

    model_config = {"from_attributes": True}


class AttendanceResponse(BaseModel):
    id: int
    user_id: int
    clock_in: datetime
    clock_out: Optional[datetime] = None
    breaks: List[AttendanceBreakResponse] = []
    date: date
    input_type: str = "web"
    note: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class AttendanceStatus(BaseModel):
    is_clocked_in: bool
    current_attendance: Optional[AttendanceResponse] = None
