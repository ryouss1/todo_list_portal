import logging
from typing import List

from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.crud import log_source as crud_log_source
from app.models.log_source import LogSource
from app.schemas.log_source import LogSourceCreate, LogSourceUpdate

logger = logging.getLogger("app.services.log_source")


def create_source(db: Session, data: LogSourceCreate) -> LogSource:
    logger.info("Creating log source: name=%s, path=%s", data.name, data.file_path)
    return crud_log_source.create_log_source(db, data)


def list_sources(db: Session) -> List[LogSource]:
    return crud_log_source.get_log_sources(db)


def get_source(db: Session, source_id: int) -> LogSource:
    source = crud_log_source.get_log_source(db, source_id)
    if not source:
        raise NotFoundError("Log source not found")
    return source


def update_source(db: Session, source_id: int, data: LogSourceUpdate) -> LogSource:
    source = get_source(db, source_id)
    logger.info("Updating log source: id=%d", source_id)
    return crud_log_source.update_log_source(db, source, data)


def delete_source(db: Session, source_id: int) -> None:
    source = get_source(db, source_id)
    logger.info("Deleting log source: id=%d", source_id)
    crud_log_source.delete_log_source(db, source)
