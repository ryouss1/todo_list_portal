from typing import List, Optional

from sqlalchemy.orm import Session

from app.models.calendar_event_attendee import CalendarEventAttendee


def get_attendees(db: Session, event_id: int) -> List[CalendarEventAttendee]:
    return db.query(CalendarEventAttendee).filter(CalendarEventAttendee.event_id == event_id).all()


def get_attendee(db: Session, event_id: int, user_id: int) -> Optional[CalendarEventAttendee]:
    return (
        db.query(CalendarEventAttendee)
        .filter(CalendarEventAttendee.event_id == event_id, CalendarEventAttendee.user_id == user_id)
        .first()
    )


def get_events_as_attendee(db: Session, user_id: int) -> List[int]:
    """Return event IDs where user is an attendee."""
    rows = db.query(CalendarEventAttendee.event_id).filter(CalendarEventAttendee.user_id == user_id).all()
    return [r[0] for r in rows]


def add_attendee(db: Session, event_id: int, user_id: int) -> CalendarEventAttendee:
    att = CalendarEventAttendee(event_id=event_id, user_id=user_id)
    db.add(att)
    db.commit()
    db.refresh(att)
    return att


def remove_attendee(db: Session, attendee: CalendarEventAttendee) -> None:
    db.delete(attendee)
    db.commit()


def update_response(db: Session, attendee: CalendarEventAttendee, status: str) -> CalendarEventAttendee:
    attendee.response_status = status
    db.commit()
    db.refresh(attendee)
    return attendee
