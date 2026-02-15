import asyncio
import logging
import os
import re
from datetime import datetime, timezone
from typing import List, Optional, Tuple

from fastapi import FastAPI
from sqlalchemy.orm import Session

from app.config import LOG_COLLECTOR_ENABLED, LOG_COLLECTOR_LOOP_INTERVAL
from app.crud import log_source as crud_log_source
from app.database import SessionLocal
from app.models.log_source import LogSource
from app.schemas.log import LogCreate
from app.services import log_service as svc_log

logger = logging.getLogger("app.services.log_collector")


def parse_log_line(line: str, source: LogSource) -> LogCreate:
    """Parse a single log line using the source's parser pattern."""
    fields = {"message": line.strip(), "severity": source.default_severity}

    if source.parser_pattern:
        match = re.match(source.parser_pattern, line.strip())
        if match:
            groups = match.groupdict()
            if "message" in groups:
                fields["message"] = groups["message"]
            if source.severity_field and source.severity_field in groups:
                fields["severity"] = groups[source.severity_field]

    return LogCreate(
        system_name=source.system_name,
        log_type=source.log_type,
        severity=fields["severity"],
        message=fields["message"],
    )


def read_new_lines(source: LogSource) -> Tuple[List[str], int, int]:
    """Read new lines from a log source file.

    Returns (lines, new_position, current_file_size).
    Handles file rotation detection.
    """
    file_path = source.file_path

    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Log file not found: {file_path}")

    current_size = os.path.getsize(file_path)
    position = source.last_read_position

    # Rotation detection: file is smaller than last known size
    if current_size < source.last_file_size:
        logger.info("File rotation detected for %s, resetting position", file_path)
        position = 0

    if current_size <= position:
        return [], position, current_size

    lines = []
    with open(file_path, "r", encoding="utf-8", errors="replace") as f:
        f.seek(position)
        new_position = position
        while True:
            line_start = f.tell()
            line = f.readline()
            if not line:
                new_position = f.tell()
                break
            if not line.endswith("\n"):
                # Incomplete line (still being written) - hold back for next poll
                new_position = line_start
                break
            lines.append(line)
            new_position = f.tell()

    return lines, new_position, current_size


async def collect_from_source(db: Session, source: LogSource) -> None:
    """Collect new log lines from a single source."""
    try:
        lines, new_position, current_size = read_new_lines(source)

        for line in lines:
            stripped = line.strip()
            if not stripped:
                continue
            log_data = parse_log_line(stripped, source)
            await svc_log.create_log(db, log_data)

        crud_log_source.update_collection_state(db, source, new_position, current_size)

    except FileNotFoundError as e:
        logger.warning("File not found for source %s: %s", source.name, e)
        crud_log_source.update_collection_state(
            db, source, source.last_read_position, source.last_file_size, error=str(e)
        )
    except Exception as e:
        logger.error("Error collecting from source %s: %s", source.name, e)
        crud_log_source.update_collection_state(
            db, source, source.last_read_position, source.last_file_size, error=str(e)
        )


async def _collector_loop() -> None:
    """Main collector loop that runs in the background."""
    logger.info("Log collector loop started (interval=%ds)", LOG_COLLECTOR_LOOP_INTERVAL)
    while True:
        try:
            db = SessionLocal()
            try:
                sources = crud_log_source.get_enabled_log_sources(db)
                now = datetime.now(timezone.utc)
                for source in sources:
                    # Check if polling interval has elapsed
                    if source.last_collected_at:
                        elapsed = (now - source.last_collected_at).total_seconds()
                        if elapsed < source.polling_interval_sec:
                            continue
                    await collect_from_source(db, source)
            finally:
                db.close()
        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.error("Error in collector loop: %s", e)

        await asyncio.sleep(LOG_COLLECTOR_LOOP_INTERVAL)


def _get_collector_task(app: FastAPI) -> Optional[asyncio.Task]:
    """Get the collector task from app.state."""
    return getattr(app.state, "collector_task", None)


def _set_collector_task(app: FastAPI, task: Optional[asyncio.Task]) -> None:
    """Set the collector task on app.state."""
    app.state.collector_task = task


async def start_collector(app: FastAPI) -> None:
    """Start the background log collector task."""
    if not LOG_COLLECTOR_ENABLED:
        logger.info("Log collector is disabled")
        return
    if _get_collector_task(app) is not None:
        logger.warning("Log collector is already running")
        return
    _set_collector_task(app, asyncio.create_task(_collector_loop()))
    logger.info("Log collector started")


async def stop_collector(app: FastAPI) -> None:
    """Stop the background log collector task."""
    task = _get_collector_task(app)
    if task is None:
        return
    task.cancel()
    try:
        await task
    except (asyncio.CancelledError, RuntimeError):
        pass
    _set_collector_task(app, None)
    logger.info("Log collector stopped")
