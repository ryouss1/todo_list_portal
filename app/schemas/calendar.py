from datetime import date, datetime
from typing import List, Literal, Optional

from pydantic import BaseModel, field_validator

# --- Event ---

EVENT_TYPES = ("event", "meeting", "deadline", "reminder", "out_of_office")
VISIBILITY_TYPES = ("public", "private")


class CalendarEventCreate(BaseModel):
    title: str
    description: Optional[str] = None
    event_type: Literal["event", "meeting", "deadline", "reminder", "out_of_office"] = "event"
    start_at: datetime
    end_at: Optional[datetime] = None
    all_day: bool = False
    room_id: Optional[int] = None
    location: Optional[str] = None
    color: Optional[str] = None
    visibility: Literal["public", "private"] = "public"
    recurrence_rule: Optional[str] = None
    recurrence_end: Optional[date] = None
    attendee_ids: Optional[List[int]] = None
    reminder_minutes: Optional[int] = None

    @field_validator("color")
    @classmethod
    def validate_color(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            v = v.strip()
            if not v.startswith("#") or len(v) != 7:
                raise ValueError("color must be #RRGGBB format")
        return v


class CalendarEventUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    event_type: Optional[Literal["event", "meeting", "deadline", "reminder", "out_of_office"]] = None
    start_at: Optional[datetime] = None
    end_at: Optional[datetime] = None
    all_day: Optional[bool] = None
    room_id: Optional[int] = None
    location: Optional[str] = None
    color: Optional[str] = None
    visibility: Optional[Literal["public", "private"]] = None
    recurrence_rule: Optional[str] = None
    recurrence_end: Optional[date] = None

    @field_validator("color")
    @classmethod
    def validate_color(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            v = v.strip()
            if not v.startswith("#") or len(v) != 7:
                raise ValueError("color must be #RRGGBB format")
        return v


class AttendeeInfo(BaseModel):
    user_id: int
    display_name: str
    response_status: str

    model_config = {"from_attributes": True}


class CalendarEventResponse(BaseModel):
    id: int
    title: str
    description: Optional[str] = None
    event_type: str
    start_at: datetime
    end_at: Optional[datetime] = None
    all_day: bool
    room_id: Optional[int] = None
    room_name: Optional[str] = None
    location: Optional[str] = None
    color: Optional[str] = None
    visibility: str
    recurrence_rule: Optional[str] = None
    recurrence_end: Optional[date] = None
    source_type: Optional[str] = None
    source_id: Optional[int] = None
    creator_id: int
    creator_name: Optional[str] = None
    attendees: List[AttendeeInfo] = []
    my_reminder_minutes: Optional[int] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class FullCalendarEvent(BaseModel):
    """FullCalendar compatible event format."""

    id: str
    title: str
    start: str
    end: Optional[str] = None
    allDay: bool = False
    color: Optional[str] = None
    textColor: Optional[str] = None
    extendedProps: dict = {}


# --- Attendee ---


class AttendeeAdd(BaseModel):
    user_ids: List[int]


class AttendeeRespond(BaseModel):
    response_status: Literal["accepted", "declined", "tentative"]


# --- Reminder ---


class ReminderSet(BaseModel):
    minutes_before: int = 10

    @field_validator("minutes_before")
    @classmethod
    def validate_minutes(cls, v: int) -> int:
        if v < 0:
            raise ValueError("minutes_before must be >= 0")
        return v


# --- Settings ---


class UserCalendarSettingResponse(BaseModel):
    default_color: str = "#3788d8"
    default_view: str = "dayGridMonth"
    default_reminder_minutes: int = 10
    show_task_list: bool = True
    show_attendance: bool = True
    show_reports: bool = False
    working_hours_start: str = "09:00"
    working_hours_end: str = "18:00"

    model_config = {"from_attributes": True}


class UserCalendarSettingUpdate(BaseModel):
    default_color: Optional[str] = None
    default_view: Optional[str] = None
    default_reminder_minutes: Optional[int] = None
    show_task_list: Optional[bool] = None
    show_attendance: Optional[bool] = None
    show_reports: Optional[bool] = None
    working_hours_start: Optional[str] = None
    working_hours_end: Optional[str] = None

    @field_validator("default_color")
    @classmethod
    def validate_color(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            v = v.strip()
            if not v.startswith("#") or len(v) != 7:
                raise ValueError("color must be #RRGGBB format")
        return v


# --- Room ---


class CalendarRoomCreate(BaseModel):
    name: str
    description: Optional[str] = None
    capacity: Optional[int] = None
    color: Optional[str] = None
    sort_order: int = 0

    @field_validator("color")
    @classmethod
    def validate_color(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            v = v.strip()
            if not v.startswith("#") or len(v) != 7:
                raise ValueError("color must be #RRGGBB format")
        return v


class CalendarRoomUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    capacity: Optional[int] = None
    color: Optional[str] = None
    sort_order: Optional[int] = None
    is_active: Optional[bool] = None

    @field_validator("color")
    @classmethod
    def validate_color(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            v = v.strip()
            if not v.startswith("#") or len(v) != 7:
                raise ValueError("color must be #RRGGBB format")
        return v


class CalendarRoomResponse(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    capacity: Optional[int] = None
    color: Optional[str] = None
    sort_order: int
    is_active: bool

    model_config = {"from_attributes": True}


class RoomReservation(BaseModel):
    event_id: int
    title: str
    start: str
    end: str
    creator_name: str


class RoomAvailability(BaseModel):
    room_id: int
    room_name: str
    date: str
    reservations: List[RoomReservation]
