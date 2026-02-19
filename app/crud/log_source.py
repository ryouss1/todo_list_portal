from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy.orm import Session

from app.crud.base import CRUDBase
from app.models.log_source import LogSource

_crud = CRUDBase(LogSource)

get_log_source = _crud.get


def create_log_source(db: Session, **kwargs) -> LogSource:
    return _crud.create(db, kwargs)


def get_log_sources(db: Session) -> List[LogSource]:
    return db.query(LogSource).order_by(LogSource.id).all()


def get_enabled_log_sources(db: Session) -> List[LogSource]:
    return db.query(LogSource).filter(LogSource.is_enabled.is_(True)).order_by(LogSource.id).all()


def update_log_source(db: Session, source: LogSource, update_data: dict) -> LogSource:
    return _crud.update(db, source, update_data)


delete_log_source = _crud.delete


def update_scan_state(
    db: Session,
    source: LogSource,
    error: Optional[str] = None,
) -> None:
    source.last_checked_at = datetime.now(timezone.utc)
    if error:
        source.last_error = error
        source.consecutive_errors = (source.consecutive_errors or 0) + 1
    else:
        source.last_error = None
        source.consecutive_errors = 0
    db.commit()


def disable_source(db: Session, source: LogSource) -> None:
    source.is_enabled = False
    db.commit()
