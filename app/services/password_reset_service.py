"""Password reset business logic.

Implements token-based password reset via email.
Security design:
- Always returns the same response regardless of whether the email exists (enumeration prevention)
- Tokens are stored as SHA-256 hashes (DB leak protection)
- Rate limited per user
- On successful reset: all tokens invalidated, all sessions invalidated, account unlocked
"""

import hashlib
import logging
import secrets
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy.orm import Session

from app import config
from app.core.auth.audit import log_auth_event
from app.core.auth.password_policy import validate_password
from app.core.exceptions import NotFoundError
from app.core.security import hash_password
from app.crud import password_reset_token as crud_token
from app.crud import user as crud_user
from app.services import email_service

logger = logging.getLogger("app.services.password_reset")


def _hash_token(raw_token: str) -> str:
    """Hash a raw token with SHA-256."""
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def _build_reset_url(raw_token: str) -> str:
    """Build the password reset URL."""
    return f"{config.PASSWORD_RESET_BASE_URL}/reset-password?token={raw_token}"


def _send_reset_email(email: str, reset_url: str) -> None:
    """Send password reset email. Falls back to logging if SMTP is not configured."""
    subject = "Todo List Portal - パスワードリセット"
    html_body = f"""
    <html>
    <body>
    <h3>パスワードリセット</h3>
    <p>パスワードリセットのリクエストを受け付けました。</p>
    <p>以下のリンクをクリックしてパスワードを再設定してください（{config.PASSWORD_RESET_EXPIRY_MINUTES}分間有効）:</p>
    <p><a href="{reset_url}">{reset_url}</a></p>
    <p>このリクエストに心当たりがない場合は、このメールを無視してください。</p>
    </body>
    </html>
    """
    text_body = (
        f"パスワードリセット\n\n"
        f"以下のURLからパスワードを再設定してください（{config.PASSWORD_RESET_EXPIRY_MINUTES}分間有効）:\n"
        f"{reset_url}\n\n"
        f"このリクエストに心当たりがない場合は、このメールを無視してください。"
    )

    sent = email_service.send_email(email, subject, html_body, text_body)
    if not sent:
        # SMTP not configured or send failed — log URL for development
        logger.info("Password reset URL for %s: %s", email, reset_url)


def request_password_reset(
    db: Session,
    email: str,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> None:
    """Request a password reset. Always succeeds (no user enumeration).

    1. Look up user by email
    2. Check rate limit
    3. Generate token, store hash in DB
    4. Commit, then send email
    """
    user = crud_user.get_user_by_email(db, email)

    if not user:
        # Log the attempt but don't reveal that the user doesn't exist
        log_auth_event(
            db,
            "password_reset_request",
            email=email,
            ip_address=ip_address,
            user_agent=user_agent,
            details={"result": "user_not_found"},
        )
        db.commit()
        return

    if not user.is_active:
        log_auth_event(
            db,
            "password_reset_request",
            user_id=user.id,
            email=email,
            ip_address=ip_address,
            user_agent=user_agent,
            details={"result": "account_disabled"},
        )
        db.commit()
        return

    # Rate limit check
    since = datetime.utcnow() - timedelta(minutes=config.PASSWORD_RESET_COOLDOWN_MINUTES)
    recent_count = crud_token.count_recent_tokens(db, user.id, since)
    if recent_count >= config.PASSWORD_RESET_MAX_REQUESTS:
        log_auth_event(
            db,
            "password_reset_request",
            user_id=user.id,
            email=email,
            ip_address=ip_address,
            user_agent=user_agent,
            details={"result": "rate_limited"},
        )
        db.commit()
        return

    # Generate token
    raw_token = secrets.token_hex(32)
    token_hash = _hash_token(raw_token)
    expires_at = datetime.utcnow() + timedelta(minutes=config.PASSWORD_RESET_EXPIRY_MINUTES)

    crud_token.create_token(db, user.id, token_hash, expires_at)

    log_auth_event(
        db,
        "password_reset_request",
        user_id=user.id,
        email=email,
        ip_address=ip_address,
        user_agent=user_agent,
        details={"result": "token_created"},
    )

    # Commit first to ensure token is persisted before sending email
    db.commit()

    # Send email (best effort — failure doesn't rollback token creation)
    reset_url = _build_reset_url(raw_token)
    _send_reset_email(email, reset_url)


def validate_reset_token(db: Session, raw_token: str) -> bool:
    """Check if a reset token is valid (exists, unused, not expired)."""
    token_hash = _hash_token(raw_token)
    token = crud_token.get_by_token_hash(db, token_hash)
    return token is not None


def complete_password_reset(
    db: Session,
    raw_token: str,
    new_password: str,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> None:
    """Complete the password reset flow.

    1. Validate token
    2. Validate password policy
    3. Update password
    4. Invalidate all tokens for the user
    5. Increment session_version (invalidate all sessions)
    6. Unlock account if locked
    7. Audit log
    """
    token_hash = _hash_token(raw_token)
    token = crud_token.get_by_token_hash(db, token_hash)

    if not token:
        raise NotFoundError("Invalid or expired reset token")

    user = crud_user.get_user(db, token.user_id)
    if not user:
        raise NotFoundError("Invalid or expired reset token")

    # Validate password policy (raises ConflictError on violation)
    validate_password(new_password)

    # Update password
    user.password_hash = hash_password(new_password)

    # Mark token as used and invalidate all other tokens for this user
    crud_token.mark_used(db, token)
    crud_token.invalidate_user_tokens(db, user.id)

    # Invalidate all sessions
    user.session_version = (user.session_version or 0) + 1

    # Unlock account if locked
    user.locked_until = None

    db.flush()

    log_auth_event(
        db,
        "password_reset_complete",
        user_id=user.id,
        email=user.email,
        ip_address=ip_address,
        user_agent=user_agent,
    )

    db.commit()
