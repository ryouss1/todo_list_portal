from datetime import datetime
from typing import List, Optional

from sqlalchemy.orm import Session

from app.models.calendar_event import CalendarEvent, CalendarEventException
from app.schemas.calendar import CalendarEventCreate, CalendarEventUpdate


def get_event(db: Session, event_id: int) -> Optional[CalendarEvent]:
    return db.query(CalendarEvent).filter(CalendarEvent.id == event_id).first()


def get_events_in_range(
    db: Session,
    start: datetime,
    end: datetime,
    user_ids: Optional[List[int]] = None,
) -> List[CalendarEvent]:
    query = db.query(CalendarEvent).filter(
        CalendarEvent.start_at < end,
        # Include events that end after start, or have no end (point events / all-day)
        ((CalendarEvent.end_at > start) | (CalendarEvent.end_at.is_(None))),
    )
    if user_ids:
        query = query.filter(CalendarEvent.creator_id.in_(user_ids))
    return query.order_by(CalendarEvent.start_at).all()


def get_recurring_events_in_range(
    db: Session,
    start: datetime,
    end: datetime,
    user_ids: Optional[List[int]] = None,
) -> List[CalendarEvent]:
    """Get events with recurrence rules that may produce occurrences in range."""
    query = db.query(CalendarEvent).filter(
        CalendarEvent.recurrence_rule.isnot(None),
        CalendarEvent.start_at < end,
        # Recurring events: either no end, or recurrence_end >= start date
        (
            (CalendarEvent.recurrence_end.is_(None))
            | (CalendarEvent.recurrence_end >= start.date() if hasattr(start, "date") else True)
        ),
    )
    if user_ids:
        query = query.filter(CalendarEvent.creator_id.in_(user_ids))
    return query.order_by(CalendarEvent.start_at).all()


def create_event(db: Session, creator_id: int, data: CalendarEventCreate) -> CalendarEvent:
    event = CalendarEvent(
        creator_id=creator_id,
        title=data.title,
        description=data.description,
        event_type=data.event_type,
        start_at=data.start_at,
        end_at=data.end_at,
        all_day=data.all_day,
        room_id=data.room_id,
        location=data.location,
        color=data.color,
        visibility=data.visibility,
        recurrence_rule=data.recurrence_rule,
        recurrence_end=data.recurrence_end,
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return event


def update_event(db: Session, event: CalendarEvent, data: CalendarEventUpdate) -> CalendarEvent:
    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(event, key, value)
    db.commit()
    db.refresh(event)
    return event


def delete_event(db: Session, event: CalendarEvent) -> None:
    db.delete(event)
    db.commit()


def get_exceptions(db: Session, parent_event_id: int) -> List[CalendarEventException]:
    return db.query(CalendarEventException).filter(CalendarEventException.parent_event_id == parent_event_id).all()


def create_exception(
    db: Session,
    parent_event_id: int,
    original_date,
    is_deleted: bool = False,
    override_event_id: Optional[int] = None,
) -> CalendarEventException:
    exc = CalendarEventException(
        parent_event_id=parent_event_id,
        original_date=original_date,
        is_deleted=is_deleted,
        override_event_id=override_event_id,
    )
    db.add(exc)
    db.commit()
    db.refresh(exc)
    return exc
