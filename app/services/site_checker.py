"""Background site health checker.

Periodically checks enabled site links using httpx.AsyncClient (fully async).
Follows the same pattern as log_scanner.py (asyncio.create_task + SessionLocal).
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Optional

from app.config import SITE_CHECKER_ENABLED, SITE_CHECKER_LOOP_INTERVAL, SITE_CHECKER_STALE_MINUTES
from app.crud import site_link as crud
from app.database import SessionLocal
from app.services.site_link_service import _perform_check
from app.services.websocket_manager import site_ws_manager

logger = logging.getLogger("app.services.site_checker")

_last_check_at: Optional[datetime] = None
_error_history: list = []  # max 10 entries, each: {"ts": str, "msg": str}
_last_error: Optional[str] = None


def _record_error(msg: str) -> None:
    """Record an error in the rolling error history (max 10 entries)."""
    global _error_history, _last_error
    _last_error = msg
    entry = {"ts": datetime.now(timezone.utc).isoformat(), "msg": msg}
    _error_history.append(entry)
    if len(_error_history) > 10:
        _error_history.pop(0)


async def _check_due_links() -> None:
    """Check all enabled links whose check interval has elapsed."""
    db = SessionLocal()
    try:
        links = crud.get_all_links(db)
        now = datetime.now(timezone.utc)

        # Build list of links that are due for a check
        due_links = []
        for link in links:
            if link.last_checked_at is not None:
                elapsed = (now - link.last_checked_at).total_seconds()
                if elapsed < link.check_interval_sec:
                    continue
            due_links.append(link)

        if not due_links:
            return

        logger.info("Checking %d due site link(s)", len(due_links))

        # Run all checks in parallel
        tasks = [_check_one(link) for link in due_links]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for link, result in zip(due_links, results):
            if isinstance(result, Exception):
                _record_error(f"link id={link.id}: {result}")
                logger.exception("Unexpected error checking link id=%d: %s", link.id, result)
                continue

            checked_at = result["checked_at"]
            previous_status = link.status
            status_changed = result["status"] != previous_status

            crud.update_link_status(
                db,
                link,
                status=result["status"],
                response_time_ms=result["response_time_ms"],
                http_status_code=result["http_status_code"],
                checked_at=checked_at,
                error_msg=result["error_msg"],
                status_changed=status_changed,
            )

            if status_changed:
                logger.info(
                    "Site link id=%d '%s' status changed: %s → %s",
                    link.id,
                    link.name,
                    previous_status,
                    result["status"],
                )
                broadcast_data = {
                    "type": "status_update",
                    "link_id": link.id,
                    "name": link.name,
                    "status": result["status"],
                    "previous_status": previous_status,
                    "response_time_ms": result["response_time_ms"],
                    "http_status_code": result["http_status_code"],
                    "checked_at": checked_at.isoformat(),
                    "message": result["message"],
                }
                await site_ws_manager.broadcast(broadcast_data)

    except Exception as exc:
        _record_error(str(exc))
        logger.exception("Error in _check_due_links")
    finally:
        db.close()


async def _check_one(link) -> dict:
    """Perform a health check for a single link. Returns result dict with checked_at."""
    result = await _perform_check(link.url, link.check_timeout_sec, link.check_ssl_verify)
    result["checked_at"] = datetime.now(timezone.utc)
    return result


async def _checker_loop() -> None:
    """Main checker loop — updates _last_check_at on every iteration."""
    global _last_check_at
    logger.info("Site checker started (loop_interval=%ds)", SITE_CHECKER_LOOP_INTERVAL)
    while True:
        _last_check_at = datetime.now(timezone.utc)
        await _check_due_links()
        await asyncio.sleep(SITE_CHECKER_LOOP_INTERVAL)


async def _watchdog_step(app) -> None:
    """Single watchdog check: restart site checker task if done or stale."""
    global _last_check_at
    task = getattr(app.state, "site_checker_task", None)
    now = datetime.now(timezone.utc)
    need_restart = False
    if task is None or task.done():
        logger.warning("Site checker task is done or missing — restarting")
        need_restart = True
    elif _last_check_at is not None:
        age_minutes = (now - _last_check_at).total_seconds() / 60
        if age_minutes > SITE_CHECKER_STALE_MINUTES:
            logger.warning(
                "Site checker loop stale (%.1f min > %d) — restarting",
                age_minutes,
                SITE_CHECKER_STALE_MINUTES,
            )
            task.cancel()
            try:
                await task
            except (asyncio.CancelledError, RuntimeError):
                pass
            need_restart = True
    if need_restart:
        _last_check_at = None  # Reset before create_task so stale-check skips "not yet started" state
        app.state.site_checker_task = asyncio.create_task(_checker_loop())


async def _watchdog_loop(app) -> None:
    """Watchdog loop: checks site checker health every 60 seconds."""
    logger.info("Site checker watchdog started")
    while True:
        await asyncio.sleep(60)
        await _watchdog_step(app)


def get_status(app) -> dict:
    """Return current status of the site checker for /api/jobs/status."""
    task = getattr(app.state, "site_checker_task", None)
    running = task is not None and not task.done()
    return {
        "name": "site_checker",
        "enabled": SITE_CHECKER_ENABLED,
        "running": running,
        "last_run_at": _last_check_at.isoformat() if _last_check_at else None,
        "error_count": len(_error_history),
        "last_error": _last_error,
    }


async def restart(app) -> dict:
    """Cancel and restart the site checker task. Returns new status."""
    global _last_check_at
    task = getattr(app.state, "site_checker_task", None)
    if task and not task.done():
        task.cancel()
        try:
            await task
        except (asyncio.CancelledError, RuntimeError):
            pass
    _last_check_at = None
    if SITE_CHECKER_ENABLED:
        app.state.site_checker_task = asyncio.create_task(_checker_loop())
    return get_status(app)


async def start_checker(app) -> None:
    """Start the site health checker background task and watchdog."""
    if not SITE_CHECKER_ENABLED:
        logger.info("Site checker disabled")
        return
    app.state.site_checker_task = asyncio.create_task(_checker_loop())
    app.state.site_checker_watchdog = asyncio.create_task(_watchdog_loop(app))
    logger.info("Site checker task and watchdog created")


async def stop_checker(app) -> None:
    """Stop the site health checker background task and watchdog."""
    for attr in ("site_checker_watchdog", "site_checker_task"):
        task = getattr(app.state, attr, None)
        if task:
            task.cancel()
            try:
                await task
            except (asyncio.CancelledError, RuntimeError):
                pass
    logger.info("Site checker stopped")
