from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from portal_core.models.login_attempt import LoginAttempt


def create_attempt(
    db: Session,
    email: str,
    success: bool,
    ip_address: Optional[str] = None,
) -> LoginAttempt:
    attempt = LoginAttempt(email=email, ip_address=ip_address, success=success)
    db.add(attempt)
    db.flush()
    return attempt


def count_recent_failures(db: Session, email: str, since: datetime) -> int:
    return (
        db.query(LoginAttempt)
        .filter(
            LoginAttempt.email == email,
            LoginAttempt.success.is_(False),
            LoginAttempt.attempted_at >= since,
        )
        .count()
    )


def delete_old_attempts(db: Session, before: datetime) -> int:
    count = db.query(LoginAttempt).filter(LoginAttempt.attempted_at < before).delete(synchronize_session=False)
    db.flush()
    return count
