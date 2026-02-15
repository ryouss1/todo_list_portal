from datetime import datetime
from typing import List, Optional

from sqlalchemy.orm import Session

from app.models.calendar_reminder import CalendarReminder


def get_reminder(db: Session, event_id: int, user_id: int) -> Optional[CalendarReminder]:
    return (
        db.query(CalendarReminder)
        .filter(CalendarReminder.event_id == event_id, CalendarReminder.user_id == user_id)
        .first()
    )


def set_reminder(
    db: Session, event_id: int, user_id: int, minutes_before: int, remind_at: datetime
) -> CalendarReminder:
    existing = get_reminder(db, event_id, user_id)
    if existing:
        existing.minutes_before = minutes_before
        existing.remind_at = remind_at
        existing.is_sent = False
        db.commit()
        db.refresh(existing)
        return existing
    reminder = CalendarReminder(
        event_id=event_id,
        user_id=user_id,
        minutes_before=minutes_before,
        remind_at=remind_at,
    )
    db.add(reminder)
    db.commit()
    db.refresh(reminder)
    return reminder


def delete_reminder(db: Session, reminder: CalendarReminder) -> None:
    db.delete(reminder)
    db.commit()


def get_pending_reminders(db: Session, now: datetime) -> List[CalendarReminder]:
    return (
        db.query(CalendarReminder).filter(CalendarReminder.remind_at <= now, CalendarReminder.is_sent.is_(False)).all()
    )


def mark_sent(db: Session, reminder: CalendarReminder) -> None:
    reminder.is_sent = True
    db.commit()
