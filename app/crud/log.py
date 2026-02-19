from typing import List

from sqlalchemy.orm import Session

from app.crud.base import CRUDBase
from app.models.log import Log
from app.schemas.log import LogCreate

_crud = CRUDBase(Log)


def create_log(db: Session, data: LogCreate) -> Log:
    return _crud.create(db, data)


def get_logs(db: Session, limit: int = 100) -> List[Log]:
    return db.query(Log).order_by(Log.received_at.desc()).limit(limit).all()


def get_important_logs(db: Session, limit: int = 100) -> List[Log]:
    return (
        db.query(Log)
        .filter(Log.severity.in_(["WARNING", "ERROR", "CRITICAL"]))
        .order_by(Log.received_at.desc())
        .limit(limit)
        .all()
    )
