"""Background log source scanner (v2).

Periodically scans enabled log sources based on their polling_interval_sec.
Follows the same pattern as reminder_checker.py (asyncio.create_task + SessionLocal).
"""

import asyncio
import logging
from datetime import datetime, timezone

from app.config import LOG_SCANNER_ENABLED, LOG_SCANNER_LOOP_INTERVAL
from app.crud import log_source as crud_log_source
from app.database import SessionLocal
from app.services import log_source_service
from app.services.websocket_manager import alert_ws_manager

logger = logging.getLogger("app.services.log_scanner")


def _scan_in_thread(source_id: int) -> dict:
    """Run scan_source in a separate thread with its own DB session.

    scan_source() performs synchronous I/O (FTP/SMB connections),
    so it must run in a thread pool to avoid blocking the event loop.
    """
    db = SessionLocal()
    try:
        return log_source_service.scan_source(db, source_id)
    finally:
        db.close()


async def _scan_due_sources() -> None:
    """Check all enabled sources and scan those whose polling interval has elapsed."""
    db = SessionLocal()
    try:
        sources = crud_log_source.get_enabled_log_sources(db)
        now = datetime.now(timezone.utc)

        for source in sources:
            # Check if polling interval has elapsed
            if source.last_checked_at is not None:
                elapsed = (now - source.last_checked_at).total_seconds()
                if elapsed < source.polling_interval_sec:
                    continue

            logger.info("Scanning source: id=%d name=%s", source.id, source.name)
            try:
                source_id = source.id
                # Run synchronous scan_source in thread pool (I/O-bound: FTP/SMB)
                result = await asyncio.to_thread(_scan_in_thread, source_id)

                # Broadcast alert via WebSocket if created
                alert_data = result.get("alert_broadcast")
                if alert_data:
                    await alert_ws_manager.broadcast({"type": "new_alert", "alert": alert_data})

                logger.info(
                    "Scan complete: source_id=%d, %s",
                    source_id,
                    result.get("message", ""),
                )
            except Exception:
                logger.exception("Error scanning source id=%d", source.id)

    except Exception:
        logger.exception("Error in scan_due_sources")
    finally:
        db.close()


async def _scanner_loop() -> None:
    """Main scanner loop."""
    logger.info("Log scanner started (loop_interval=%ds)", LOG_SCANNER_LOOP_INTERVAL)
    while True:
        await _scan_due_sources()
        await asyncio.sleep(LOG_SCANNER_LOOP_INTERVAL)


async def start_scanner(app) -> None:
    """Start the log scanner background task."""
    if not LOG_SCANNER_ENABLED:
        logger.info("Log scanner disabled")
        return
    app.state.log_scanner_task = asyncio.create_task(_scanner_loop())
    logger.info("Log scanner task created")


async def stop_scanner(app) -> None:
    """Stop the log scanner background task."""
    task = getattr(app.state, "log_scanner_task", None)
    if task:
        task.cancel()
        try:
            await task
        except (asyncio.CancelledError, RuntimeError):
            pass
        logger.info("Log scanner stopped")
