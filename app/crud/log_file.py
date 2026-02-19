from datetime import datetime
from typing import List, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.log_file import LogFile


def get_files_by_source(
    db: Session,
    source_id: int,
    status: Optional[str] = None,
) -> List[LogFile]:
    q = db.query(LogFile).filter(LogFile.source_id == source_id)
    if status:
        q = q.filter(LogFile.status == status)
    return q.order_by(LogFile.file_modified_at.desc().nullslast(), LogFile.file_name).all()


def get_files_by_path(
    db: Session,
    path_id: int,
    status: Optional[str] = None,
) -> List[LogFile]:
    q = db.query(LogFile).filter(LogFile.path_id == path_id)
    if status:
        q = q.filter(LogFile.status == status)
    return q.order_by(LogFile.file_modified_at.desc().nullslast(), LogFile.file_name).all()


def get_file(db: Session, file_id: int) -> Optional[LogFile]:
    return db.query(LogFile).filter(LogFile.id == file_id).first()


def get_file_by_source_and_name(db: Session, source_id: int, file_name: str) -> Optional[LogFile]:
    return db.query(LogFile).filter(LogFile.source_id == source_id, LogFile.file_name == file_name).first()


def get_file_by_path_and_name(db: Session, path_id: int, file_name: str) -> Optional[LogFile]:
    return db.query(LogFile).filter(LogFile.path_id == path_id, LogFile.file_name == file_name).first()


def upsert_file(
    db: Session,
    source_id: int,
    path_id: int,
    file_name: str,
    file_size: int,
    file_modified_at: Optional[datetime],
    status: str,
) -> LogFile:
    existing = get_file_by_path_and_name(db, path_id, file_name)
    if existing:
        existing.file_size = file_size
        existing.file_modified_at = file_modified_at
        existing.status = status
        db.flush()
        return existing
    else:
        log_file = LogFile(
            source_id=source_id,
            path_id=path_id,
            file_name=file_name,
            file_size=file_size,
            file_modified_at=file_modified_at,
            status=status,
        )
        db.add(log_file)
        db.flush()
        return log_file


def mark_missing_files_deleted(db: Session, source_id: int, active_file_names: List[str]) -> None:
    """Mark files not in active_file_names as deleted (source-level)."""
    if active_file_names:
        db.query(LogFile).filter(
            LogFile.source_id == source_id,
            LogFile.file_name.notin_(active_file_names),
            LogFile.status != "deleted",
        ).update({"status": "deleted"}, synchronize_session="fetch")
    else:
        db.query(LogFile).filter(
            LogFile.source_id == source_id,
            LogFile.status != "deleted",
        ).update({"status": "deleted"}, synchronize_session="fetch")


def mark_missing_files_deleted_for_path(db: Session, path_id: int, active_file_names: List[str]) -> None:
    """Mark files not in active_file_names as deleted (path-level)."""
    if active_file_names:
        db.query(LogFile).filter(
            LogFile.path_id == path_id,
            LogFile.file_name.notin_(active_file_names),
            LogFile.status != "deleted",
        ).update({"status": "deleted"}, synchronize_session="fetch")
    else:
        db.query(LogFile).filter(
            LogFile.path_id == path_id,
            LogFile.status != "deleted",
        ).update({"status": "deleted"}, synchronize_session="fetch")


def get_changed_files_by_path(db: Session, path_id: int) -> List[LogFile]:
    """Get new or updated files for a given path."""
    return (
        db.query(LogFile)
        .filter(
            LogFile.path_id == path_id,
            LogFile.status.in_(["new", "updated"]),
        )
        .order_by(LogFile.file_name)
        .all()
    )


def count_files_by_source(db: Session, source_id: int) -> dict:
    """Return file counts by status for a source."""
    rows = (
        db.query(LogFile.status, func.count(LogFile.id))
        .filter(LogFile.source_id == source_id)
        .group_by(LogFile.status)
        .all()
    )
    counts = {row[0]: row[1] for row in rows}
    return {
        "total": sum(counts.values()),
        "new": counts.get("new", 0),
        "updated": counts.get("updated", 0),
        "unchanged": counts.get("unchanged", 0),
        "deleted": counts.get("deleted", 0),
        "error": counts.get("error", 0),
    }


def reset_files_for_reread(db: Session, source_id: int) -> int:
    """Reset last_read_line and file_modified_at for all files belonging to the source.

    Setting file_modified_at to None ensures scan_source detects files as 'updated',
    triggering content re-reading.
    """
    count = (
        db.query(LogFile)
        .filter(LogFile.source_id == source_id)
        .update({"last_read_line": 0, "file_modified_at": None}, synchronize_session="fetch")
    )
    db.flush()
    return count


def update_last_read_line(db: Session, log_file: LogFile, line_number: int) -> None:
    log_file.last_read_line = line_number
    db.flush()
