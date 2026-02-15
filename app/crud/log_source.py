from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy.orm import Session

from app.models.log_source import LogSource
from app.schemas.log_source import LogSourceCreate, LogSourceUpdate


def create_log_source(db: Session, data: LogSourceCreate) -> LogSource:
    source = LogSource(**data.model_dump())
    db.add(source)
    db.commit()
    db.refresh(source)
    return source


def get_log_sources(db: Session) -> List[LogSource]:
    return db.query(LogSource).order_by(LogSource.id).all()


def get_enabled_log_sources(db: Session) -> List[LogSource]:
    return db.query(LogSource).filter(LogSource.is_enabled.is_(True)).order_by(LogSource.id).all()


def get_log_source(db: Session, source_id: int) -> Optional[LogSource]:
    return db.query(LogSource).filter(LogSource.id == source_id).first()


def update_log_source(db: Session, source: LogSource, data: LogSourceUpdate) -> LogSource:
    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(source, key, value)
    db.commit()
    db.refresh(source)
    return source


def delete_log_source(db: Session, source: LogSource) -> None:
    db.delete(source)
    db.commit()


def update_collection_state(
    db: Session,
    source: LogSource,
    position: int,
    file_size: int,
    error: Optional[str] = None,
) -> None:
    source.last_read_position = position
    source.last_file_size = file_size
    source.last_collected_at = datetime.now(timezone.utc)
    source.last_error = error
    db.commit()
