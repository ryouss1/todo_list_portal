import logging
from typing import List

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.auth.audit import log_auth_event
from app.core.auth.password_policy import validate_password
from app.core.constants import UserRole
from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError
from app.core.security import hash_password, verify_password
from app.crud import group as crud_group
from app.crud import user as crud_user
from app.models.user import User
from app.schemas.user import UserCreate, UserResponse, UserUpdate

logger = logging.getLogger("app.services.user")


def _build_group_map(db: Session) -> dict:
    groups = crud_group.get_groups(db)
    return {g.id: g.name for g in groups}


def _to_response(user: User, group_map: dict) -> UserResponse:
    return UserResponse(
        id=user.id,
        email=user.email,
        display_name=user.display_name,
        role=user.role,
        is_active=user.is_active,
        group_id=user.group_id,
        group_name=group_map.get(user.group_id) if user.group_id else None,
        created_at=user.created_at,
        updated_at=user.updated_at,
    )


def list_users(db: Session) -> List[UserResponse]:
    logger.info("Listing users")
    users = crud_user.get_users(db)
    group_map = _build_group_map(db)
    return [_to_response(u, group_map) for u in users]


def get_user(db: Session, user_id: int) -> User:
    user = crud_user.get_user(db, user_id)
    if not user:
        logger.warning("User not found: id=%d", user_id)
        raise NotFoundError("User not found")
    return user


def get_user_response(db: Session, user_id: int) -> UserResponse:
    user = get_user(db, user_id)
    group_map = _build_group_map(db)
    return _to_response(user, group_map)


def create_user(db: Session, data: UserCreate) -> User:
    logger.info("Creating user: email=%s", data.email)
    validate_password(data.password)
    try:
        user = crud_user.create_user(db, data)
    except IntegrityError:
        db.rollback()
        logger.warning("Duplicate email: %s", data.email)
        raise ConflictError("Email already exists")
    logger.info("User created: id=%d", user.id)
    return user


def update_user(db: Session, user_id: int, data: UserUpdate, current_user_id: int) -> UserResponse:
    current_user = crud_user.get_user(db, current_user_id)
    is_admin = current_user and current_user.role == UserRole.ADMIN
    is_self = user_id == current_user_id

    update_data = data.model_dump(exclude_unset=True)
    if not update_data:
        return get_user_response(db, user_id)

    if not is_admin:
        if not is_self:
            raise ForbiddenError("Cannot edit other users")
        # Non-admin: only display_name and preferred_locale allowed
        update_data = {k: v for k, v in update_data.items() if k in {"display_name", "preferred_locale"}}
        if not update_data:
            raise ForbiddenError("Cannot change these fields")
    else:
        # Admin editing self: cannot change own role or active status
        if is_self and ("role" in update_data or "is_active" in update_data):
            raise ForbiddenError("Cannot change own role or active status")

    # Invalidate sessions if role or is_active changed
    invalidate_session = "role" in update_data or "is_active" in update_data

    user = crud_user.update_user(db, user_id, update_data)
    if not user:
        raise NotFoundError("User not found")

    if invalidate_session:
        _increment_session_version(db, user_id)
        if "role" in update_data:
            log_auth_event(db, "role_changed", user_id=user_id, details={"new_role": update_data["role"]})
        if "is_active" in update_data:
            log_auth_event(db, "session_invalidated", user_id=user_id, details={"is_active": update_data["is_active"]})

    logger.info("User updated: id=%d, fields=%s", user_id, list(update_data.keys()))
    group_map = _build_group_map(db)
    return _to_response(user, group_map)


def _increment_session_version(db: Session, user_id: int) -> None:
    """Increment session_version to invalidate all existing sessions."""
    user = crud_user.get_user(db, user_id)
    if user:
        user.session_version = (user.session_version or 1) + 1
        db.flush()


def change_password(db: Session, user_id: int, current_password: str, new_password: str) -> User:
    user = get_user(db, user_id)
    if not verify_password(current_password, user.password_hash):
        raise ConflictError("Current password is incorrect")
    validate_password(new_password)
    new_hash = hash_password(new_password)
    crud_user.update_password(db, user_id, new_hash)
    _increment_session_version(db, user_id)
    log_auth_event(db, "password_change", user_id=user_id)
    logger.info("Password changed: user_id=%d", user_id)
    return user


def reset_password(db: Session, user_id: int, new_password: str) -> User:
    user = get_user(db, user_id)
    validate_password(new_password)
    new_hash = hash_password(new_password)
    crud_user.update_password(db, user_id, new_hash)
    _increment_session_version(db, user_id)
    log_auth_event(db, "password_reset", user_id=user_id)
    logger.info("Password reset by admin: user_id=%d", user_id)
    return user


def unlock_user(db: Session, user_id: int) -> None:
    from app.core.auth.rate_limiter import unlock_account

    user = get_user(db, user_id)
    unlock_account(db, user)
    log_auth_event(db, "account_unlocked", user_id=user_id)
    db.commit()
    logger.info("Account unlocked by admin: user_id=%d", user_id)


def delete_user(db: Session, user_id: int, current_user_id: int) -> None:
    if user_id == current_user_id:
        raise ForbiddenError("Cannot delete yourself")
    user = crud_user.get_user(db, user_id)
    if not user:
        raise NotFoundError("User not found")
    crud_user.delete_user(db, user_id)
    logger.info("User deleted: id=%d", user_id)
