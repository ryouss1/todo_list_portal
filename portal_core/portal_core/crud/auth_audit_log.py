from typing import List, Optional

from sqlalchemy.orm import Session

from portal_core.models.auth_audit_log import AuthAuditLog


def create_log(
    db: Session,
    event_type: str,
    user_id: Optional[int] = None,
    email: Optional[str] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    details: Optional[dict] = None,
) -> AuthAuditLog:
    log = AuthAuditLog(
        user_id=user_id,
        event_type=event_type,
        email=email,
        ip_address=ip_address,
        user_agent=user_agent,
        details=details,
    )
    db.add(log)
    db.flush()
    return log


def get_logs(
    db: Session,
    limit: int = 100,
    user_id: Optional[int] = None,
    event_type: Optional[str] = None,
) -> List[AuthAuditLog]:
    query = db.query(AuthAuditLog)
    if user_id is not None:
        query = query.filter(AuthAuditLog.user_id == user_id)
    if event_type:
        query = query.filter(AuthAuditLog.event_type == event_type)
    return query.order_by(AuthAuditLog.created_at.desc()).limit(limit).all()
