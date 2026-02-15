from datetime import date, datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.deps import get_current_user_id, require_admin
from app.database import get_db
from app.schemas.calendar import (
    AttendeeAdd,
    AttendeeInfo,
    AttendeeRespond,
    CalendarEventCreate,
    CalendarEventResponse,
    CalendarEventUpdate,
    CalendarRoomCreate,
    CalendarRoomResponse,
    CalendarRoomUpdate,
    FullCalendarEvent,
    ReminderSet,
    RoomAvailability,
    UserCalendarSettingResponse,
    UserCalendarSettingUpdate,
)
from app.services import calendar_service as svc

router = APIRouter(prefix="/api/calendar", tags=["calendar"])


# --- Rooms (must be before /events/{event_id} to avoid path conflicts) ---


@router.get("/rooms", response_model=List[CalendarRoomResponse])
def list_active_rooms(
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    return svc.get_active_rooms(db)


@router.get("/rooms/all", response_model=List[CalendarRoomResponse])
def list_all_rooms(
    db: Session = Depends(get_db),
    user_id: int = Depends(require_admin),
):
    return svc.get_all_rooms(db)


@router.post("/rooms", response_model=CalendarRoomResponse, status_code=201)
def create_room(
    data: CalendarRoomCreate,
    db: Session = Depends(get_db),
    user_id: int = Depends(require_admin),
):
    return svc.create_room(db, data.name, data.description, data.capacity, data.color, data.sort_order)


@router.put("/rooms/{room_id}", response_model=CalendarRoomResponse)
def update_room(
    room_id: int,
    data: CalendarRoomUpdate,
    db: Session = Depends(get_db),
    user_id: int = Depends(require_admin),
):
    return svc.update_room(db, room_id, data)


@router.delete("/rooms/{room_id}", status_code=204)
def delete_room(
    room_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(require_admin),
):
    svc.delete_room(db, room_id)


@router.get("/rooms/{room_id}/availability", response_model=RoomAvailability)
def get_room_availability(
    room_id: int,
    target_date: date = Query(..., alias="date"),
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    return svc.get_room_availability(db, room_id, target_date)


# --- Events ---


@router.get("/events", response_model=List[FullCalendarEvent])
def list_events(
    start: datetime = Query(...),
    end: datetime = Query(...),
    user_ids: Optional[str] = Query(None),
    include_source: bool = Query(True),
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    parsed_user_ids = None
    if user_ids:
        parsed_user_ids = [int(x.strip()) for x in user_ids.split(",") if x.strip()]
    return svc.list_events_fullcalendar(db, user_id, start, end, parsed_user_ids, include_source)


@router.post("/events", response_model=CalendarEventResponse, status_code=201)
def create_event(
    data: CalendarEventCreate,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    return svc.create_event(db, user_id, data)


@router.get("/events/{event_id}", response_model=CalendarEventResponse)
def get_event(
    event_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    return svc.get_event(db, event_id, user_id)


@router.put("/events/{event_id}", response_model=CalendarEventResponse)
def update_event(
    event_id: int,
    data: CalendarEventUpdate,
    scope: str = Query("all"),
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    return svc.update_event(db, event_id, user_id, data, scope)


@router.delete("/events/{event_id}", status_code=204)
def delete_event(
    event_id: int,
    scope: str = Query("all"),
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    svc.delete_event(db, event_id, user_id, scope)


# --- Attendees ---


@router.post("/events/{event_id}/attendees", response_model=List[AttendeeInfo])
def add_attendees(
    event_id: int,
    data: AttendeeAdd,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    return svc.add_attendees(db, event_id, user_id, data.user_ids)


@router.delete("/events/{event_id}/attendees/{target_user_id}", status_code=204)
def remove_attendee(
    event_id: int,
    target_user_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    svc.remove_attendee(db, event_id, user_id, target_user_id)


@router.patch("/events/{event_id}/respond", response_model=AttendeeInfo)
def respond_to_event(
    event_id: int,
    data: AttendeeRespond,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    return svc.respond_to_event(db, event_id, user_id, data.response_status)


# --- Reminders ---


@router.put("/events/{event_id}/reminder", status_code=204)
def set_reminder(
    event_id: int,
    data: ReminderSet,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    svc.set_reminder(db, event_id, user_id, data.minutes_before)


@router.delete("/events/{event_id}/reminder", status_code=204)
def delete_reminder(
    event_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    svc.delete_reminder(db, event_id, user_id)


# --- Settings ---


@router.get("/settings", response_model=UserCalendarSettingResponse)
def get_settings(
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    return svc.get_settings(db, user_id)


@router.put("/settings", response_model=UserCalendarSettingResponse)
def update_settings(
    data: UserCalendarSettingUpdate,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    return svc.update_settings(db, user_id, data)
