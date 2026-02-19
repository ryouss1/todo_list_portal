from datetime import datetime, timedelta, timezone
from typing import List, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.log_entry import LogEntry


def create_entries_batch(db: Session, entries: List[dict]) -> int:
    """Bulk insert log entries. Returns count of inserted rows."""
    if not entries:
        return 0
    db.bulk_insert_mappings(LogEntry, entries)
    db.flush()
    return len(entries)


def get_entries_by_file(
    db: Session,
    file_id: int,
    after_line: int = 0,
    limit: int = 500,
) -> List[LogEntry]:
    """Get entries for a file, cursor-based (after line_number)."""
    q = db.query(LogEntry).filter(LogEntry.file_id == file_id)
    if after_line > 0:
        q = q.filter(LogEntry.line_number > after_line)
    return q.order_by(LogEntry.line_number).limit(limit).all()


def count_entries_by_file(db: Session, file_id: int) -> int:
    return db.query(func.count(LogEntry.id)).filter(LogEntry.file_id == file_id).scalar() or 0


def search_entries(
    db: Session,
    source_id: Optional[int] = None,
    file_id: Optional[int] = None,
    severity: Optional[str] = None,
    keyword: Optional[str] = None,
    from_date: Optional[datetime] = None,
    to_date: Optional[datetime] = None,
    after_id: int = 0,
    limit: int = 100,
) -> List[LogEntry]:
    """Search log entries with cursor-based pagination."""
    from app.models.log_file import LogFile

    q = db.query(LogEntry)
    if source_id is not None:
        q = q.join(LogFile, LogEntry.file_id == LogFile.id).filter(LogFile.source_id == source_id)
    if file_id is not None:
        q = q.filter(LogEntry.file_id == file_id)
    if severity:
        q = q.filter(LogEntry.severity == severity)
    if keyword:
        q = q.filter(LogEntry.message.ilike(f"%{keyword}%"))
    if from_date:
        q = q.filter(LogEntry.received_at >= from_date)
    if to_date:
        q = q.filter(LogEntry.received_at <= to_date)
    if after_id > 0:
        q = q.filter(LogEntry.id > after_id)
    return q.order_by(LogEntry.id).limit(limit).all()


def count_search_entries(
    db: Session,
    source_id: Optional[int] = None,
    file_id: Optional[int] = None,
    severity: Optional[str] = None,
    keyword: Optional[str] = None,
    from_date: Optional[datetime] = None,
    to_date: Optional[datetime] = None,
) -> int:
    """Count matching entries for search."""
    from app.models.log_file import LogFile

    q = db.query(func.count(LogEntry.id))
    if source_id is not None:
        q = q.join(LogFile, LogEntry.file_id == LogFile.id).filter(LogFile.source_id == source_id)
    if file_id is not None:
        q = q.filter(LogEntry.file_id == file_id)
    if severity:
        q = q.filter(LogEntry.severity == severity)
    if keyword:
        q = q.filter(LogEntry.message.ilike(f"%{keyword}%"))
    if from_date:
        q = q.filter(LogEntry.received_at >= from_date)
    if to_date:
        q = q.filter(LogEntry.received_at <= to_date)
    return q.scalar() or 0


def delete_entries_by_source(db: Session, source_id: int) -> int:
    """Delete all log entries belonging to files of the given source."""
    from sqlalchemy import select

    from app.models.log_file import LogFile

    file_ids_stmt = select(LogFile.id).where(LogFile.source_id == source_id)
    count = db.query(LogEntry).filter(LogEntry.file_id.in_(file_ids_stmt)).delete(synchronize_session="fetch")
    db.flush()
    return count


def delete_old_entries(db: Session, retention_days: int) -> int:
    """Delete entries older than retention_days. Returns deleted count."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=retention_days)
    count = db.query(LogEntry).filter(LogEntry.received_at < cutoff).delete(synchronize_session="fetch")
    db.commit()
    return count
