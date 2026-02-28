from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from portal_core.models.oauth_state import OAuthState


def create_state(
    db: Session,
    state: str,
    expires_at: datetime,
    code_verifier: Optional[str] = None,
    redirect_uri: Optional[str] = None,
) -> OAuthState:
    obj = OAuthState(
        state=state,
        code_verifier=code_verifier,
        redirect_uri=redirect_uri,
        expires_at=expires_at,
    )
    db.add(obj)
    db.flush()
    return obj


def consume_state(db: Session, state: str) -> Optional[OAuthState]:
    """Find and delete a state token. Returns None if not found or expired."""
    obj = db.query(OAuthState).filter(OAuthState.state == state).first()
    if not obj:
        return None
    if obj.expires_at < datetime.now(timezone.utc):
        db.delete(obj)
        db.flush()
        return None
    db.delete(obj)
    db.flush()
    return obj


def cleanup_expired(db: Session) -> int:
    count = (
        db.query(OAuthState)
        .filter(OAuthState.expires_at < datetime.now(timezone.utc))
        .delete(synchronize_session=False)
    )
    db.flush()
    return count
