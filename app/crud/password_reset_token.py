from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from app.models.password_reset_token import PasswordResetToken


def create_token(db: Session, user_id: int, token_hash: str, expires_at: datetime) -> PasswordResetToken:
    token = PasswordResetToken(
        user_id=user_id,
        token_hash=token_hash,
        expires_at=expires_at,
    )
    db.add(token)
    db.flush()
    return token


def get_by_token_hash(db: Session, token_hash: str) -> Optional[PasswordResetToken]:
    """Get a valid (unused, not expired) token by its hash."""
    now = datetime.utcnow()
    return (
        db.query(PasswordResetToken)
        .filter(
            PasswordResetToken.token_hash == token_hash,
            PasswordResetToken.is_used == False,  # noqa: E712
            PasswordResetToken.expires_at > now,
        )
        .first()
    )


def mark_used(db: Session, token: PasswordResetToken) -> None:
    token.is_used = True
    db.flush()


def invalidate_user_tokens(db: Session, user_id: int) -> int:
    """Mark all unused tokens for a user as used. Returns count of invalidated tokens."""
    count = (
        db.query(PasswordResetToken)
        .filter(
            PasswordResetToken.user_id == user_id,
            PasswordResetToken.is_used == False,  # noqa: E712
        )
        .update({"is_used": True})
    )
    db.flush()
    return count


def count_recent_tokens(db: Session, user_id: int, since: datetime) -> int:
    """Count tokens created since a given time (for rate limiting)."""
    return (
        db.query(PasswordResetToken)
        .filter(
            PasswordResetToken.user_id == user_id,
            PasswordResetToken.created_at >= since,
        )
        .count()
    )


def cleanup_expired(db: Session) -> int:
    """Delete expired and used tokens. Returns count of deleted tokens."""
    now = datetime.utcnow()
    count = (
        db.query(PasswordResetToken)
        .filter(
            PasswordResetToken.is_used == True,  # noqa: E712
            PasswordResetToken.expires_at < now,
        )
        .delete()
    )
    db.flush()
    return count
