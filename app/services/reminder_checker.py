import asyncio
import logging
from datetime import datetime, timezone
from typing import Optional

from app.config import CALENDAR_REMINDER_ENABLED, CALENDAR_REMINDER_INTERVAL, CALENDAR_REMINDER_STALE_MINUTES
from app.crud import calendar_event as crud_event
from app.crud import calendar_reminder as crud_reminder
from app.database import SessionLocal
from app.services.websocket_manager import calendar_ws_manager

logger = logging.getLogger("app.services.reminder_checker")

_WATCHDOG_INTERVAL = 120  # seconds between watchdog checks

_last_check_at: Optional[datetime] = None


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
    """Main loop for checking reminders — updates _last_check_at each iteration."""
    global _last_check_at
    logger.info("Reminder checker started (interval=%ds)", CALENDAR_REMINDER_INTERVAL)
    while True:
        _last_check_at = datetime.now(timezone.utc)
        await _check_reminders()
        await asyncio.sleep(CALENDAR_REMINDER_INTERVAL)


async def _watchdog_step(app) -> None:
    """Single watchdog check: restart reminder task if done or stale."""
    global _last_check_at
    task = getattr(app.state, "reminder_task", None)
    now = datetime.now(timezone.utc)
    need_restart = False

    if task is None or task.done():
        logger.warning("Reminder task is done or missing — restarting")
        need_restart = True
    elif _last_check_at is not None:
        age_minutes = (now - _last_check_at).total_seconds() / 60
        if age_minutes > CALENDAR_REMINDER_STALE_MINUTES:
            logger.warning(
                "Reminder loop stale (%.1f min > %d) — restarting",
                age_minutes,
                CALENDAR_REMINDER_STALE_MINUTES,
            )
            task.cancel()
            try:
                await task
            except (asyncio.CancelledError, RuntimeError):
                pass
            need_restart = True

    if need_restart:
        _last_check_at = None  # Reset before create_task so stale-check skips "not yet started" state
        app.state.reminder_task = asyncio.create_task(_reminder_loop())


async def _watchdog_loop(app) -> None:
    """Watchdog loop: checks reminder health every _WATCHDOG_INTERVAL seconds."""
    logger.info("Reminder checker watchdog started")
    while True:
        await asyncio.sleep(_WATCHDOG_INTERVAL)
        await _watchdog_step(app)


def get_status(app) -> dict:
    """Return current status of the reminder checker for /api/jobs/status."""
    task = getattr(app.state, "reminder_task", None)
    enabled = CALENDAR_REMINDER_ENABLED
    running = task is not None and not task.done()
    return {
        "name": "reminder_checker",
        "enabled": enabled,
        "running": running,
        "last_run_at": _last_check_at.isoformat() if _last_check_at else None,
    }


async def start_reminder_checker(app) -> None:
    """Start the reminder checker background task and watchdog."""
    if not CALENDAR_REMINDER_ENABLED:
        logger.info("Reminder checker disabled")
        return
    app.state.reminder_task = asyncio.create_task(_reminder_loop())
    app.state.reminder_watchdog = asyncio.create_task(_watchdog_loop(app))
    logger.info("Reminder checker task and watchdog created")


async def stop_reminder_checker(app) -> None:
    """Stop the reminder checker background task and watchdog."""
    for attr in ("reminder_watchdog", "reminder_task"):
        task = getattr(app.state, attr, None)
        if task:
            task.cancel()
            try:
                await task
            except (asyncio.CancelledError, RuntimeError):
                pass
    logger.info("Reminder checker stopped")
