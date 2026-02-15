from datetime import datetime
from typing import List, Optional

from sqlalchemy.orm import Session

from app.models.calendar_event import CalendarEvent
from app.models.calendar_room import CalendarRoom


def get_room(db: Session, room_id: int) -> Optional[CalendarRoom]:
    return db.query(CalendarRoom).filter(CalendarRoom.id == room_id).first()


def get_active_rooms(db: Session) -> List[CalendarRoom]:
    return db.query(CalendarRoom).filter(CalendarRoom.is_active.is_(True)).order_by(CalendarRoom.sort_order).all()


def get_all_rooms(db: Session) -> List[CalendarRoom]:
    return db.query(CalendarRoom).order_by(CalendarRoom.sort_order).all()


def create_room(
    db: Session,
    name: str,
    description: Optional[str] = None,
    capacity: Optional[int] = None,
    color: Optional[str] = None,
    sort_order: int = 0,
) -> CalendarRoom:
    room = CalendarRoom(name=name, description=description, capacity=capacity, color=color, sort_order=sort_order)
    db.add(room)
    db.commit()
    db.refresh(room)
    return room


def update_room(db: Session, room: CalendarRoom, data: dict) -> CalendarRoom:
    for key, value in data.items():
        setattr(room, key, value)
    db.commit()
    db.refresh(room)
    return room


def check_room_conflict(
    db: Session,
    room_id: int,
    start_at: datetime,
    end_at: datetime,
    exclude_event_id: Optional[int] = None,
) -> Optional[CalendarEvent]:
    """Check if a room has a conflicting reservation. Returns the conflicting event or None."""
    query = db.query(CalendarEvent).filter(
        CalendarEvent.room_id == room_id,
        CalendarEvent.start_at < end_at,
        CalendarEvent.end_at > start_at,
        CalendarEvent.end_at.isnot(None),
    )
    if exclude_event_id:
        query = query.filter(CalendarEvent.id != exclude_event_id)
    return query.first()


def get_room_reservations(db: Session, room_id: int, date_start: datetime, date_end: datetime) -> List[CalendarEvent]:
    return (
        db.query(CalendarEvent)
        .filter(
            CalendarEvent.room_id == room_id,
            CalendarEvent.start_at < date_end,
            CalendarEvent.end_at > date_start,
            CalendarEvent.end_at.isnot(None),
        )
        .order_by(CalendarEvent.start_at)
        .all()
    )
