"""Login rate limiting and account lockout."""

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy.orm import Session

from portal_core import config
from portal_core.core.exceptions import AuthenticationError, ConflictError
from portal_core.crud import login_attempt as crud_attempt
from portal_core.models.user import User

logger = logging.getLogger("app.core.auth.rate_limiter")


def check_rate_limit(db: Session, email: str) -> None:
    """Check if login attempts for this email exceed the rate limit.

    Raises ConflictError if the threshold is exceeded within the window.
    """
    window_start = datetime.now(timezone.utc) - timedelta(minutes=config.LOGIN_RATE_LIMIT_WINDOW_MINUTES)
    failures = crud_attempt.count_recent_failures(db, email, window_start)
    if failures >= config.LOGIN_MAX_ATTEMPTS:
        raise ConflictError(
            f"Too many login attempts. Please try again after {config.LOGIN_RATE_LIMIT_WINDOW_MINUTES} minutes"
        )


def record_attempt(
    db: Session,
    email: str,
    success: bool,
    ip_address: Optional[str] = None,
) -> None:
    """Record a login attempt."""
    crud_attempt.create_attempt(db, email, success, ip_address)


def check_account_locked(db: Session, user: User) -> None:
    """Check if the user account is currently locked.

    Raises AuthenticationError if locked.
    """
    if user.locked_until and user.locked_until > datetime.now(timezone.utc):
        raise AuthenticationError("Account is locked. Please try again later")


def maybe_lock_account(db: Session, user: User) -> bool:
    """Lock the account if failure count exceeds threshold. Returns True if locked."""
    window_start = datetime.now(timezone.utc) - timedelta(minutes=config.LOGIN_RATE_LIMIT_WINDOW_MINUTES)
    failures = crud_attempt.count_recent_failures(db, user.email, window_start)
    if failures >= config.LOGIN_MAX_ATTEMPTS:
        user.locked_until = datetime.now(timezone.utc) + timedelta(minutes=config.ACCOUNT_LOCKOUT_MINUTES)
        db.flush()
        logger.warning("Account locked: user_id=%d, email=%s", user.id, user.email)
        return True
    return False


def unlock_account(db: Session, user: User) -> None:
    """Unlock a user account (admin action)."""
    user.locked_until = None
    db.flush()
    logger.info("Account unlocked: user_id=%d", user.id)


def cleanup_old_attempts(db: Session, days: int = 90) -> int:
    """Delete login attempts older than the specified number of days."""
    before = datetime.now(timezone.utc) - timedelta(days=days)
    return crud_attempt.delete_old_attempts(db, before)
