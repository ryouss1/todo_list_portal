"""Authentication audit logging."""

import logging
from typing import Optional

from sqlalchemy.orm import Session

from portal_core.crud import auth_audit_log as crud_audit

logger = logging.getLogger("app.core.auth.audit")


def log_auth_event(
    db: Session,
    event_type: str,
    user_id: Optional[int] = None,
    email: Optional[str] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    details: Optional[dict] = None,
) -> None:
    """Record an authentication audit event."""
    try:
        crud_audit.create_log(
            db,
            event_type=event_type,
            user_id=user_id,
            email=email,
            ip_address=ip_address,
            user_agent=user_agent,
            details=details,
        )
    except Exception:
        logger.exception("Failed to write audit log: event_type=%s", event_type)
