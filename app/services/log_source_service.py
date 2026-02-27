"""Log source management service (v2 with remote connections + multi-path)."""

import functools
import logging
import re
import signal
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Dict, List, Optional

from sqlalchemy.orm import Session

from app.config import (
    LOG_ALERT_CONTENT_DISPLAY_LINES,
    LOG_ALERT_CONTENT_MAX_LINES,
    LOG_SCAN_PATH_TIMEOUT,
    LOG_SOURCE_MAX_CONSECUTIVE_FAILURES,
)
from app.constants import DEFAULT_LOG_FILE_PATTERN, AccessMethod
from app.core.encryption import decrypt_value, encrypt_value, is_encryption_available, mask_username
from app.core.exceptions import ConflictError, NotFoundError
from app.crud import log_entry as crud_log_entry
from app.crud import log_file as crud_log_file
from app.crud import log_source as crud_log_source
from app.crud import log_source_path as crud_path
from app.models.log_source import LogSource
from app.schemas.log_source import LogSourceCreate, LogSourceUpdate
from app.services.remote_connector import create_connector

logger = logging.getLogger("app.services.log_source")


class ScanTimeoutError(Exception):
    """Raised when a per-path scan exceeds the configured timeout."""

    pass


@contextmanager
def _path_timeout(seconds: int):
    """Context manager that raises ScanTimeoutError after `seconds`.

    Uses SIGALRM on Unix. On platforms without SIGALRM (Windows) or
    when called from a non-main thread, timeout is skipped (no-op).
    """
    if seconds <= 0 or not hasattr(signal, "SIGALRM"):
        yield
        return

    def _handler(signum, frame):
        raise ScanTimeoutError(f"Path scan timed out after {seconds}s")

    try:
        old_handler = signal.signal(signal.SIGALRM, _handler)
    except ValueError:
        # signal.signal() only works in main thread
        yield
        return

    signal.alarm(seconds)
    try:
        yield
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, old_handler)


def _generate_folder_link(access_method: str, host: str, port: Optional[int], base_path: str) -> str:
    """Generate a navigable folder link based on access method.

    SMB: file://///host/path/ (opens in Windows Explorer)
    FTP: ftp://host:port/path/
    """
    # Normalize path separators
    normalized = base_path.replace("\\", "/").strip("/")

    if access_method == AccessMethod.SMB:
        return f"file://///{host}/{normalized}/"
    else:
        # FTP
        port_str = f":{port}" if port and port != 21 else ""
        return f"ftp://{host}{port_str}/{normalized}/"


def _generate_copy_path(access_method: str, host: str, port: Optional[int], base_path: str) -> str:
    """Generate a clipboard-friendly path for the folder.

    SMB: \\\\host\\share\\path\\  (UNC path for Explorer address bar)
    FTP: ftp://host:port/path/
    """
    if access_method == AccessMethod.SMB:
        # Build UNC path with backslashes
        normalized = base_path.replace("/", "\\").strip("\\")
        return f"\\\\{host}\\{normalized}\\"
    else:
        normalized = base_path.replace("\\", "/").strip("/")
        port_str = f":{port}" if port and port != 21 else ""
        return f"ftp://{host}{port_str}/{normalized}/"


@functools.lru_cache(maxsize=32)
def _compile_pattern(pattern: str) -> re.Pattern:
    """Compile a regex pattern with LRU cache to avoid repeated compilation."""
    return re.compile(pattern)


def _parse_log_line(
    line: str,
    parser_pattern: Optional[str],
    severity_field: Optional[str],
    default_severity: str,
) -> dict:
    """Parse a log line and extract severity using parser_pattern."""
    severity = default_severity
    if parser_pattern and severity_field:
        try:
            compiled = _compile_pattern(parser_pattern)
            m = compiled.match(line)
            if m and severity_field in m.groupdict():
                severity = m.group(severity_field).upper()
        except re.error:
            pass
    return {"severity": severity, "message": line}


def _read_alert_file_content(
    connector,
    source,
    path,
    log_file,
    db: Session,
    max_lines: int,
) -> List[dict]:
    """Read file content for alert-target files and store in log_entries.

    Returns list of read entry dicts (for alert message inclusion).
    """
    offset = log_file.last_read_line  # 0 for new files

    try:
        lines = connector.read_lines(
            path.base_path,
            log_file.file_name,
            offset=offset,
            limit=max_lines,
            encoding=source.encoding,
        )
    except Exception as e:
        logger.warning(
            "Failed to read file content: source=%d path=%s file=%s: %s",
            source.id,
            path.base_path,
            log_file.file_name,
            e,
        )
        return []

    if not lines:
        return []

    entries = []
    for i, line in enumerate(lines):
        line_number = offset + i + 1
        parsed = _parse_log_line(line, source.parser_pattern, source.severity_field, source.default_severity)
        entries.append(
            {
                "file_id": log_file.id,
                "line_number": line_number,
                "severity": parsed["severity"],
                "message": parsed["message"],
            }
        )

    # Bulk insert entries
    crud_log_entry.create_entries_batch(db, entries)

    # Update last_read_line
    new_last_line = offset + len(lines)
    crud_log_file.update_last_read_line(db, log_file, new_last_line)

    return entries


def create_source(db: Session, data: LogSourceCreate) -> dict:
    """Create a new log source with encrypted credentials and paths."""
    if not is_encryption_available():
        raise ConflictError("Encryption key is not configured. Cannot store credentials.")

    # Encrypt credentials
    encrypted_username = encrypt_value(data.username)
    encrypted_password = encrypt_value(data.password)

    source = crud_log_source.create_log_source(
        db,
        name=data.name,
        group_id=data.group_id,
        access_method=data.access_method,
        host=data.host,
        port=data.port,
        username=encrypted_username,
        password=encrypted_password,
        domain=data.domain,
        encoding=data.encoding,
        source_type=data.source_type,
        polling_interval_sec=data.polling_interval_sec,
        collection_mode=data.collection_mode,
        parser_pattern=data.parser_pattern,
        severity_field=data.severity_field,
        default_severity=data.default_severity,
        is_enabled=data.is_enabled,
        alert_on_change=data.alert_on_change,
    )

    # Create paths
    for p in data.paths:
        crud_path.create_path(
            db,
            source_id=source.id,
            base_path=p.base_path,
            file_pattern=p.file_pattern,
            is_enabled=p.is_enabled,
        )
    db.commit()
    db.refresh(source)

    return _to_response_dict(db, source)


def list_sources(db: Session) -> List[dict]:
    sources = crud_log_source.get_log_sources(db)
    if not sources:
        return []
    group_map = _build_group_map(db)
    source_ids = [s.id for s in sources]
    paths_map = crud_path.get_paths_by_source_ids(db, source_ids)
    return [_to_response_dict(db, s, group_map=group_map, paths_list=paths_map.get(s.id, [])) for s in sources]


def get_source(db: Session, source_id: int) -> dict:
    source = _get_source_or_raise(db, source_id)
    return _to_response_dict(db, source)


def get_source_model(db: Session, source_id: int) -> LogSource:
    """Get raw model (for internal use by scanner etc.)."""
    return _get_source_or_raise(db, source_id)


def update_source(db: Session, source_id: int, data: LogSourceUpdate) -> dict:
    source = _get_source_or_raise(db, source_id)
    update_data = data.model_dump(exclude_unset=True)

    # Extract paths from update_data (handled separately)
    paths_data = update_data.pop("paths", None)

    # Encrypt credentials if provided
    if "username" in update_data and update_data["username"] is not None:
        update_data["username"] = encrypt_value(update_data["username"])
    if "password" in update_data and update_data["password"] is not None:
        update_data["password"] = encrypt_value(update_data["password"])

    logger.info("Updating log source: id=%d", source_id)

    # Update source fields
    if update_data:
        source = crud_log_source.update_log_source(db, source, update_data)

    # Reconcile paths if provided
    if paths_data is not None:
        _reconcile_paths(db, source.id, paths_data)
        db.commit()
        db.refresh(source)

    return _to_response_dict(db, source)


def delete_source(db: Session, source_id: int) -> None:
    source = _get_source_or_raise(db, source_id)
    logger.info("Deleting log source: id=%d", source_id)
    crud_log_source.delete_log_source(db, source)


def test_connection(db: Session, source_id: int) -> dict:
    """Test remote connection for each path and return per-path results."""
    source = _get_source_or_raise(db, source_id)
    try:
        username = decrypt_value(source.username)
        password = decrypt_value(source.password)
    except Exception as e:
        return {
            "status": "error",
            "file_count": 0,
            "message": f"Decryption failed: {e}",
            "path_results": [],
        }

    paths = crud_path.get_paths_by_source(db, source.id)
    if not paths:
        return {
            "status": "error",
            "file_count": 0,
            "message": "No paths configured",
            "path_results": [],
        }

    path_results = []
    total_files = 0
    all_ok = True

    try:
        connector = create_connector(
            access_method=source.access_method,
            host=source.host,
            port=source.port,
            username=username,
            password=password,
            domain=source.domain,
        )
        with connector:
            for p in paths:
                try:
                    files = connector.list_files(p.base_path, p.file_pattern)
                    path_results.append(
                        {
                            "base_path": p.base_path,
                            "file_pattern": p.file_pattern,
                            "status": "ok",
                            "file_count": len(files),
                            "message": f"Found {len(files)} files",
                        }
                    )
                    total_files += len(files)
                except Exception as e:
                    path_results.append(
                        {
                            "base_path": p.base_path,
                            "file_pattern": p.file_pattern,
                            "status": "error",
                            "file_count": 0,
                            "message": str(e),
                        }
                    )
                    all_ok = False
    except Exception as e:
        return {
            "status": "error",
            "file_count": 0,
            "message": str(e),
            "path_results": [],
        }

    overall_status = "ok" if all_ok else "error"
    if all_ok:
        message = f"Connected successfully. Found {total_files} files across {len(paths)} paths."
    else:
        ok_count = sum(1 for r in path_results if r["status"] == "ok")
        message = f"Partial success: {ok_count}/{len(paths)} paths ok, {total_files} files found."

    # Update last_checked_at on successful test
    if all_ok:
        source.last_checked_at = datetime.now(timezone.utc)
        db.commit()

    return {
        "status": overall_status,
        "file_count": total_files,
        "message": message,
        "path_results": path_results,
    }


def _build_group_map(db: Session) -> dict:
    """Build a dict mapping group_id -> group_name."""
    from app.crud import group as crud_group

    groups = crud_group.get_groups(db)
    return {g.id: g.name for g in groups}


_EMPTY_FILE_COUNTS: Dict[str, int] = {
    "total": 0,
    "new": 0,
    "updated": 0,
    "unchanged": 0,
    "deleted": 0,
    "error": 0,
}


def list_source_statuses(db: Session) -> List[dict]:
    """Get source statuses with file counts and changed path details for dashboard table."""
    sources = crud_log_source.get_log_sources(db)
    if not sources:
        return []

    source_ids = [s.id for s in sources]
    group_map = _build_group_map(db)

    # Batch-fetch file counts, paths, and changed files in 3 queries total
    counts_map: Dict[int, dict] = crud_log_file.count_files_all_sources(db, source_ids)
    paths_map: Dict[int, list] = crud_path.get_paths_by_source_ids(db, source_ids)

    # Collect all path IDs that belong to alert-enabled sources
    alert_path_ids = []
    for source in sources:
        if source.alert_on_change and source.is_enabled:
            for p in paths_map.get(source.id, []):
                alert_path_ids.append(p.id)
    changed_files_map: Dict[int, list] = crud_log_file.get_changed_files_by_path_ids(db, alert_path_ids)

    result = []
    for source in sources:
        counts = counts_map.get(source.id, _EMPTY_FILE_COUNTS)
        paths = paths_map.get(source.id, [])
        new_count = counts["new"]
        updated_count = counts["updated"]
        has_alert = source.alert_on_change and source.is_enabled and (new_count > 0 or updated_count > 0)

        changed_paths = []
        if has_alert:
            for p in paths:
                changed_files = changed_files_map.get(p.id, [])
                if changed_files:
                    path_new = [f.file_name for f in changed_files if f.status == "new"]
                    path_updated = [f.file_name for f in changed_files if f.status == "updated"]
                    changed_paths.append(
                        {
                            "path_id": p.id,
                            "base_path": p.base_path,
                            "folder_link": _generate_folder_link(
                                source.access_method, source.host, source.port, p.base_path
                            ),
                            "copy_path": _generate_copy_path(
                                source.access_method, source.host, source.port, p.base_path
                            ),
                            "new_files": path_new,
                            "updated_files": path_updated,
                        }
                    )

        result.append(
            {
                "id": source.id,
                "name": source.name,
                "group_id": source.group_id,
                "group_name": group_map.get(source.group_id, ""),
                "access_method": source.access_method,
                "host": source.host,
                "source_type": source.source_type,
                "collection_mode": source.collection_mode,
                "is_enabled": source.is_enabled,
                "alert_on_change": source.alert_on_change,
                "consecutive_errors": source.consecutive_errors,
                "last_checked_at": source.last_checked_at,
                "last_error": source.last_error,
                "path_count": len(paths),
                "file_count": counts["total"],
                "new_file_count": new_count,
                "updated_file_count": updated_count,
                "has_alert": has_alert,
                "changed_paths": changed_paths,
            }
        )
    return result


def scan_source(db: Session, source_id: int) -> dict:
    """Scan a source: connect to remote, list files, upsert DB, optionally create alerts."""
    source = _get_source_or_raise(db, source_id)

    try:
        username = decrypt_value(source.username)
        password = decrypt_value(source.password)
    except Exception as e:
        crud_log_source.update_scan_state(
            db, source, error=f"Decryption failed: {e}", max_failures=LOG_SOURCE_MAX_CONSECUTIVE_FAILURES
        )
        return {
            "file_count": 0,
            "new_count": 0,
            "updated_count": 0,
            "alerts_created": 0,
            "message": f"Decryption failed: {e}",
            "changed_paths": [],
            "content_read_files": 0,
            "alert_broadcast": None,
        }

    enabled_paths = crud_path.get_enabled_paths_by_source(db, source.id)
    if not enabled_paths:
        crud_log_source.update_scan_state(db, source, error=None)
        return {
            "file_count": 0,
            "new_count": 0,
            "updated_count": 0,
            "alerts_created": 0,
            "message": "No enabled paths configured",
            "changed_paths": [],
            "content_read_files": 0,
            "alert_broadcast": None,
        }

    # Use UTC date to match timezone-aware datetime comparisons
    today = datetime.now(timezone.utc).date()
    total_new = 0
    total_updated = 0
    total_files = 0
    # Track per-path changes for changed_paths response
    per_path_changes: dict = {}  # path_id -> {base_path, new_files, updated_files}
    path_errors: List[str] = []

    try:
        connector = create_connector(
            access_method=source.access_method,
            host=source.host,
            port=source.port,
            username=username,
            password=password,
            domain=source.domain,
        )
        with connector:
            for p in enabled_paths:
                try:
                    with _path_timeout(LOG_SCAN_PATH_TIMEOUT):
                        # Pass modified_since for early date filtering inside connector
                        remote_files = connector.list_files(p.base_path, p.file_pattern, modified_since=today)
                except ScanTimeoutError:
                    logger.warning(
                        "Path scan timed out: source_id=%d path=%s (timeout=%ds)",
                        source.id,
                        p.base_path,
                        LOG_SCAN_PATH_TIMEOUT,
                    )
                    path_errors.append(f"{p.base_path}: timed out after {LOG_SCAN_PATH_TIMEOUT}s")
                    continue
                except Exception as path_err:
                    logger.warning(
                        "Path scan error: source_id=%d path=%s: %s",
                        source.id,
                        p.base_path,
                        path_err,
                    )
                    path_errors.append(f"{p.base_path}: {path_err}")
                    continue

                logger.info(
                    "Scan path: source_id=%d path=%s found %d files (modified_since=%s)",
                    source.id,
                    p.base_path,
                    len(remote_files),
                    today,
                )

                active_names = []
                path_new_files: List[str] = []
                path_updated_files: List[str] = []

                # Pre-fetch all existing files for this path in one query
                existing_files = {f.file_name: f for f in crud_log_file.get_files_by_path(db, p.id)}

                for rf in remote_files:
                    existing = existing_files.get(rf.name)
                    if existing:
                        if existing.file_size != rf.size or existing.file_modified_at != rf.modified_at:
                            status = "updated"
                            total_updated += 1
                            path_updated_files.append(rf.name)
                        else:
                            status = "unchanged"
                        crud_log_file.update_file(db, existing, rf.size, rf.modified_at, status)
                    else:
                        status = "new"
                        total_new += 1
                        path_new_files.append(rf.name)
                        crud_log_file.create_file(
                            db,
                            source_id=source.id,
                            path_id=p.id,
                            file_name=rf.name,
                            file_size=rf.size,
                            file_modified_at=rf.modified_at,
                            status=status,
                        )
                    active_names.append(rf.name)
                    total_files += 1

                # Mark files not in today's list as deleted for this path
                crud_log_file.mark_missing_files_deleted_for_path(db, p.id, active_names)

                # Track changes for this path
                if path_new_files or path_updated_files:
                    per_path_changes[p.id] = {
                        "base_path": p.base_path,
                        "new_files": path_new_files,
                        "updated_files": path_updated_files,
                    }

            # --- Content reading phase (alert_on_change only) ---
            content_read_files = 0
            all_read_entries: List[dict] = []

            if source.alert_on_change and (total_new > 0 or total_updated > 0):
                enabled_path_ids = [p.id for p in enabled_paths]
                changed_files_map = crud_log_file.get_changed_files_by_path_ids(db, enabled_path_ids)
                for p in enabled_paths:
                    changed_files = changed_files_map.get(p.id, [])
                    for log_file in changed_files:
                        entries = _read_alert_file_content(
                            connector, source, p, log_file, db, LOG_ALERT_CONTENT_MAX_LINES
                        )
                        if entries:
                            content_read_files += 1
                            # Keep last N entries per file for alert message
                            all_read_entries.extend(entries[-LOG_ALERT_CONTENT_DISPLAY_LINES:])

                logger.info("Content read: %d files for source_id=%d", content_read_files, source.id)

        db.commit()
        error_msg = "; ".join(path_errors) if path_errors else None
        crud_log_source.update_scan_state(db, source, error=error_msg)

    except Exception as e:
        # Expire all to discard any partial flushes
        db.expire_all()
        crud_log_source.update_scan_state(db, source, error=str(e), max_failures=LOG_SOURCE_MAX_CONSECUTIVE_FAILURES)
        return {
            "file_count": 0,
            "new_count": 0,
            "updated_count": 0,
            "alerts_created": 0,
            "message": f"Scan failed: {e}",
            "changed_paths": [],
            "content_read_files": 0,
            "alert_broadcast": None,
        }

    # Build changed_paths with folder links
    changed_paths = []
    for path_id, pdata in per_path_changes.items():
        changed_paths.append(
            {
                "path_id": path_id,
                "base_path": pdata["base_path"],
                "folder_link": _generate_folder_link(
                    source.access_method, source.host, source.port, pdata["base_path"]
                ),
                "copy_path": _generate_copy_path(source.access_method, source.host, source.port, pdata["base_path"]),
                "new_files": pdata["new_files"],
                "updated_files": pdata["updated_files"],
            }
        )

    # Create alert if alert_on_change is enabled and changes detected
    alerts_created = 0
    alert_broadcast = None
    if source.alert_on_change and (total_new > 0 or total_updated > 0):
        try:
            from app.constants import AlertSeverity as AlertSeverityConst
            from app.crud import alert as crud_alert
            from app.schemas.alert import AlertCreate

            # Build detailed alert message with file names and folder paths
            detail_lines = []
            for cp in changed_paths:
                all_files = cp["new_files"] + cp["updated_files"]
                file_list = ", ".join(all_files)
                detail_lines.append(f"{cp['base_path']}: {file_list}")
            detail_text = "\n".join(detail_lines) if detail_lines else ""

            alert_msg = f"Source '{source.name}': {total_new} new, {total_updated} updated files.\n{detail_text}"

            # Append content summary if available
            if all_read_entries:
                alert_msg += "\n\n--- Log Content ---\n"
                content_lines = [e["message"] for e in all_read_entries[-LOG_ALERT_CONTENT_DISPLAY_LINES:]]
                alert_msg += "\n".join(content_lines)

            alert_create_data = AlertCreate(
                title=f"[{source.name}] File changes detected",
                message=alert_msg,
                severity=AlertSeverityConst.WARNING,
                source=f"log_source:{source.id}",
            )
            alert = crud_alert.create_alert(db, alert_create_data)
            alerts_created = 1
            alert_broadcast = {
                "id": alert.id,
                "title": alert.title,
                "message": alert.message,
                "severity": alert.severity,
                "source": alert.source,
                "rule_id": alert.rule_id,
                "is_active": alert.is_active,
                "acknowledged": alert.acknowledged,
                "created_at": alert.created_at.isoformat(),
            }
        except Exception as e:
            logger.warning("Failed to create scan alert: %s", e)

    parts = []
    if total_new > 0:
        parts.append(f"{total_new} new")
    if total_updated > 0:
        parts.append(f"{total_updated} updated")
    unchanged = total_files - total_new - total_updated
    if unchanged > 0:
        parts.append(f"{unchanged} unchanged")
    detail = ", ".join(parts) if parts else "no files"
    message = f"Scan completed: {total_files} files ({detail})"
    if path_errors:
        message += f"; {len(path_errors)} path error(s)"

    return {
        "file_count": total_files,
        "new_count": total_new,
        "updated_count": total_updated,
        "alerts_created": alerts_created,
        "message": message,
        "changed_paths": changed_paths,
        "content_read_files": content_read_files,
        "alert_broadcast": alert_broadcast,
    }


def re_read_source(db: Session, source_id: int) -> dict:
    """Clear existing log entries, reset read positions, and re-scan the source.

    Used after encoding changes to re-import content with correct settings.
    """
    _get_source_or_raise(db, source_id)

    deleted_count = crud_log_entry.delete_entries_by_source(db, source_id)
    reset_count = crud_log_file.reset_files_for_reread(db, source_id)
    db.commit()

    logger.info(
        "Re-read: source_id=%d deleted %d entries, reset %d files",
        source_id,
        deleted_count,
        reset_count,
    )

    return scan_source(db, source_id)


def list_files(db: Session, source_id: int, status: Optional[str] = None) -> list:
    """List files for a source."""
    _get_source_or_raise(db, source_id)
    return crud_log_file.get_files_by_source(db, source_id, status)


def _get_source_or_raise(db: Session, source_id: int) -> LogSource:
    source = crud_log_source.get_log_source(db, source_id)
    if not source:
        raise NotFoundError("Log source not found")
    return source


def _reconcile_paths(db: Session, source_id: int, paths_data: list) -> None:
    """Reconcile paths: update existing, create new, delete missing."""
    existing_paths = crud_path.get_paths_by_source(db, source_id)
    existing_by_id = {p.id: p for p in existing_paths}

    # Track which existing IDs are still present
    seen_ids = set()

    for p_data in paths_data:
        path_id = p_data.get("id")
        if path_id and path_id in existing_by_id:
            # Update existing path
            seen_ids.add(path_id)
            path = existing_by_id[path_id]
            crud_path.update_path(
                db,
                path,
                {
                    "base_path": p_data["base_path"],
                    "file_pattern": p_data.get("file_pattern", DEFAULT_LOG_FILE_PATTERN),
                    "is_enabled": p_data.get("is_enabled", True),
                },
            )
        else:
            # Create new path
            crud_path.create_path(
                db,
                source_id=source_id,
                base_path=p_data["base_path"],
                file_pattern=p_data.get("file_pattern", DEFAULT_LOG_FILE_PATTERN),
                is_enabled=p_data.get("is_enabled", True),
            )

    # Delete paths not in the new list
    for existing_id, path in existing_by_id.items():
        if existing_id not in seen_ids:
            crud_path.delete_path(db, path)


def _to_response_dict(
    db: Session,
    source: LogSource,
    group_map: Optional[Dict] = None,
    paths_list: Optional[list] = None,
) -> dict:
    """Convert source model to response dict with masked username and paths."""
    try:
        plain_username = decrypt_value(source.username)
        masked = mask_username(plain_username)
    except Exception:
        masked = "****"

    if paths_list is None:
        paths_list = crud_path.get_paths_by_source(db, source.id)

    paths_list_data = [
        {
            "id": p.id,
            "source_id": p.source_id,
            "base_path": p.base_path,
            "file_pattern": p.file_pattern,
            "is_enabled": p.is_enabled,
            "created_at": p.created_at,
            "updated_at": p.updated_at,
        }
        for p in paths_list
    ]

    if group_map is None:
        group_map = _build_group_map(db)

    return {
        "id": source.id,
        "name": source.name,
        "group_id": source.group_id,
        "group_name": group_map.get(source.group_id, ""),
        "access_method": source.access_method,
        "host": source.host,
        "port": source.port,
        "username_masked": masked,
        "domain": source.domain,
        "paths": paths_list_data,
        "encoding": source.encoding,
        "source_type": source.source_type,
        "polling_interval_sec": source.polling_interval_sec,
        "collection_mode": source.collection_mode,
        "parser_pattern": source.parser_pattern,
        "severity_field": source.severity_field,
        "default_severity": source.default_severity,
        "is_enabled": source.is_enabled,
        "alert_on_change": source.alert_on_change,
        "consecutive_errors": source.consecutive_errors,
        "last_checked_at": source.last_checked_at,
        "last_error": source.last_error,
        "created_at": source.created_at,
        "updated_at": source.updated_at,
    }
