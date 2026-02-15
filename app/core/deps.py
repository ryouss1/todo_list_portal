from fastapi import Depends, Request
from sqlalchemy.orm import Session

from app.core.exceptions import AuthenticationError, ForbiddenError
from app.database import get_db


def get_current_user_id(request: Request, db: Session = Depends(get_db)) -> int:
    """セッションからuser_idを取得し、session_versionを検証。未認証なら401。"""
    user_id = request.session.get("user_id")
    if not user_id:
        raise AuthenticationError()

    from app.models.user import User

    user = db.query(User.session_version, User.is_active).filter(User.id == user_id).first()
    if not user or not user.is_active:
        request.session.clear()
        raise AuthenticationError()

    session_ver = request.session.get("session_version", 0)
    if user.session_version != session_ver:
        request.session.clear()
        raise AuthenticationError("Session expired")

    return user_id


def require_admin(user_id: int = Depends(get_current_user_id), db: Session = Depends(get_db)) -> int:
    """管理者権限を要求。admin以外は403。"""
    from app.models.user import User

    user = db.query(User).filter(User.id == user_id).first()
    if not user or user.role != "admin":
        raise ForbiddenError("Admin access required")
    return user_id
