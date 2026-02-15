from typing import List

from sqlalchemy.orm import Session

from app.models.log import Log
from app.schemas.log import LogCreate


def create_log(db: Session, data: LogCreate) -> Log:
    log = Log(**data.model_dump())
    db.add(log)
    db.commit()
    db.refresh(log)
    return log


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
