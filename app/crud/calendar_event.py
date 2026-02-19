from datetime import datetime
from typing import List, Optional

from sqlalchemy.orm import Session

from app.crud.base import CRUDBase
from app.models.calendar_event import CalendarEvent, CalendarEventException
from app.schemas.calendar import CalendarEventCreate, CalendarEventUpdate

_crud = CRUDBase(CalendarEvent)

get_event = _crud.get


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
    # Exclude non-model fields (attendee_ids, reminder_minutes are handled separately by service)
    event_data = data.model_dump(exclude={"attendee_ids", "reminder_minutes"})
    return _crud.create(db, event_data, creator_id=creator_id)


def update_event(db: Session, event: CalendarEvent, data: CalendarEventUpdate) -> CalendarEvent:
    return _crud.update(db, event, data)


delete_event = _crud.delete


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
