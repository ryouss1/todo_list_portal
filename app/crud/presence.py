from typing import List, Optional

from sqlalchemy.orm import Session

from app.models.presence import PresenceLog, PresenceStatus


def get_presence_status(db: Session, user_id: int) -> Optional[PresenceStatus]:
    return db.query(PresenceStatus).filter(PresenceStatus.user_id == user_id).first()


def get_all_presence_statuses(db: Session) -> List[PresenceStatus]:
    return db.query(PresenceStatus).all()


def upsert_presence_status(db: Session, user_id: int, status: str, message: Optional[str] = None) -> PresenceStatus:
    existing = get_presence_status(db, user_id)
    if existing:
        existing.status = status
        existing.message = message
    else:
        existing = PresenceStatus(user_id=user_id, status=status, message=message)
        db.add(existing)
    db.commit()
    db.refresh(existing)
    return existing


def create_presence_log(db: Session, user_id: int, status: str, message: Optional[str] = None) -> PresenceLog:
    log = PresenceLog(user_id=user_id, status=status, message=message)
    db.add(log)
    db.commit()
    db.refresh(log)
    return log


def get_presence_logs(db: Session, user_id: int, limit: int = 50) -> List[PresenceLog]:
    return (
        db.query(PresenceLog)
        .filter(PresenceLog.user_id == user_id)
        .order_by(PresenceLog.changed_at.desc())
        .limit(limit)
        .all()
    )
