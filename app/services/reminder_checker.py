import asyncio
import logging
from datetime import datetime, timezone

from app.config import CALENDAR_REMINDER_ENABLED, CALENDAR_REMINDER_INTERVAL
from app.crud import calendar_event as crud_event
from app.crud import calendar_reminder as crud_reminder
from app.database import SessionLocal
from app.services.websocket_manager import calendar_ws_manager

logger = logging.getLogger("app.services.reminder_checker")


async def _check_reminders() -> None:
    """Check for pending reminders and send notifications via WebSocket."""
    db = SessionLocal()
    try:
        now = datetime.now(timezone.utc)
        pending = crud_reminder.get_pending_reminders(db, now)

        for reminder in pending:
            event = crud_event.get_event(db, reminder.event_id)
            if not event:
                crud_reminder.mark_sent(db, reminder)
                continue

            message = {
                "type": "calendar_reminder",
                "event_id": event.id,
                "title": event.title,
                "start": event.start_at.isoformat(),
                "minutes_before": reminder.minutes_before,
                "location": event.location,
                "user_id": reminder.user_id,
            }
            await calendar_ws_manager.broadcast(message)
            crud_reminder.mark_sent(db, reminder)
            logger.info(
                "Reminder sent: event_id=%d, user_id=%d, minutes_before=%d",
                event.id,
                reminder.user_id,
                reminder.minutes_before,
            )
    except Exception:
        logger.exception("Error checking reminders")
    finally:
        db.close()


async def _reminder_loop() -> None:
    """Main loop for checking reminders."""
    logger.info("Reminder checker started (interval=%ds)", CALENDAR_REMINDER_INTERVAL)
    while True:
        await _check_reminders()
        await asyncio.sleep(CALENDAR_REMINDER_INTERVAL)


async def start_reminder_checker(app) -> None:
    """Start the reminder checker background task."""
    if not CALENDAR_REMINDER_ENABLED:
        logger.info("Reminder checker disabled")
        return
    app.state.reminder_task = asyncio.create_task(_reminder_loop())
    logger.info("Reminder checker task created")


async def stop_reminder_checker(app) -> None:
    """Stop the reminder checker background task."""
    task = getattr(app.state, "reminder_task", None)
    if task:
        task.cancel()
        try:
            await task
        except (asyncio.CancelledError, RuntimeError):
            pass
        logger.info("Reminder checker stopped")
