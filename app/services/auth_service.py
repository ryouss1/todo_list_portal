from typing import Optional

from sqlalchemy.orm import Session

from app.core.auth.audit import log_auth_event
from app.core.auth.rate_limiter import (
    check_account_locked,
    check_rate_limit,
    maybe_lock_account,
    record_attempt,
)
from app.core.exceptions import AuthenticationError
from app.core.security import verify_password
from app.crud import user as crud_user
from app.models.user import User


def authenticate(
    db: Session,
    email: str,
    password: str,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> User:
    # 1. Check rate limit (too many failures for this email)
    check_rate_limit(db, email)

    # 2. Find user
    user = crud_user.get_user_by_email(db, email)
    if not user or not user.password_hash:
        record_attempt(db, email, success=False, ip_address=ip_address)
        log_auth_event(db, "login_failure", email=email, ip_address=ip_address, user_agent=user_agent)
        raise AuthenticationError("Invalid email or password")

    # 3. Check if account is locked
    check_account_locked(db, user)

    # 4. Verify password
    if not verify_password(password, user.password_hash):
        record_attempt(db, email, success=False, ip_address=ip_address)
        locked = maybe_lock_account(db, user)
        if locked:
            log_auth_event(
                db,
                "account_locked",
                user_id=user.id,
                email=email,
                ip_address=ip_address,
                user_agent=user_agent,
            )
        log_auth_event(
            db,
            "login_failure",
            user_id=user.id,
            email=email,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        raise AuthenticationError("Invalid email or password")

    # 5. Check active status
    if not user.is_active:
        record_attempt(db, email, success=False, ip_address=ip_address)
        log_auth_event(
            db,
            "login_failure",
            user_id=user.id,
            email=email,
            ip_address=ip_address,
            user_agent=user_agent,
            details={"reason": "account_disabled"},
        )
        raise AuthenticationError("Account is disabled")

    # 6. Success
    record_attempt(db, email, success=True, ip_address=ip_address)
    log_auth_event(
        db,
        "login_success",
        user_id=user.id,
        email=email,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    return user
