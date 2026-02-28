from typing import Callable, Optional

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from portal_core.core.constants import UserRole
from portal_core.core.exceptions import AuthenticationError, ForbiddenError
from portal_core.database import get_db


def get_optional_user_id(request: Request, db: Session = Depends(get_db)) -> Optional[int]:
    """Get user_id from session without raising 401 for unauthenticated users.

    Returns None when the request has no valid session (unauthenticated).
    Used for endpoints that are publicly accessible (e.g. wiki public pages)
    but still behave differently for authenticated users.
    """
    user_id = request.session.get("user_id")
    if not user_id:
        return None

    from portal_core.models.user import User

    user = db.query(User.session_version, User.is_active).filter(User.id == user_id).first()
    if not user or not user.is_active:
        request.session.clear()
        return None

    session_ver = request.session.get("session_version", 0)
    if user.session_version != session_ver:
        request.session.clear()
        return None

    return user_id


def get_current_user_id(request: Request, db: Session = Depends(get_db)) -> int:
    """Get user_id from session and validate session_version. Raises 401 if not authenticated."""
    user_id = request.session.get("user_id")
    if not user_id:
        raise AuthenticationError()

    from portal_core.models.user import User

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
    """Require admin role or wildcard RBAC permission.

    Passes if EITHER condition is met:
    1. user.role == 'admin' (legacy role-based check)
    2. has_permission(db, user_id, '*', '*') — RBAC wildcard grant

    This unifies the legacy role check with future-proof RBAC permission check.
    Raises 403 for users who satisfy neither condition.
    """
    from portal_core.crud.role import has_permission
    from portal_core.models.user import User

    row = db.query(User.role).filter(User.id == user_id).first()
    if not row:
        raise ForbiddenError("Admin access required")
    if row.role == UserRole.ADMIN:
        return user_id
    if has_permission(db, user_id, "*", "*"):
        return user_id
    raise ForbiddenError("Admin access required")


def require_permission(resource: str, action: str) -> Callable:
    """Factory returning a FastAPI dependency that checks resource+action permission.

    Precedence:
    1. Legacy admin role (user.role == 'admin') — always passes (backward compat)
    2. has_permission() via user_roles + role_permissions
    """

    def _check(
        user_id: int = Depends(get_current_user_id),
        db: Session = Depends(get_db),
    ) -> int:
        from portal_core.crud.role import has_permission
        from portal_core.models.user import User

        row = db.query(User.role).filter(User.id == user_id).first()
        if not row:
            raise ForbiddenError(f"Permission required: {resource}:{action}")
        # Legacy admin bypass
        if row.role == UserRole.ADMIN:
            return user_id
        if not has_permission(db, user_id, resource, action):
            raise ForbiddenError(f"Permission required: {resource}:{action}")
        return user_id

    return _check
