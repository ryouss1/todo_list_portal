from typing import List

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from portal_core.core.deps import get_current_user_id, require_admin
from portal_core.core.exceptions import NotFoundError
from portal_core.crud import role as crud_role
from portal_core.database import get_db
from portal_core.schemas.role import RoleResponse
from portal_core.schemas.user import PasswordChange, PasswordReset, UserCreate, UserResponse, UserUpdate
from portal_core.services import user_service as svc_user

router = APIRouter(prefix="/api/users", tags=["users"])


@router.get("/", response_model=List[UserResponse])
def list_users(db: Session = Depends(get_db), _user_id: int = Depends(get_current_user_id)):
    return svc_user.list_users(db)


@router.post("/", response_model=UserResponse, status_code=201)
def create_user(data: UserCreate, db: Session = Depends(get_db), _user_id: int = Depends(require_admin)):
    return svc_user.create_user(db, data)


@router.put("/me/password")
def change_my_password(
    data: PasswordChange, db: Session = Depends(get_db), user_id: int = Depends(get_current_user_id)
):
    svc_user.change_password(db, user_id, data.current_password, data.new_password)
    return {"detail": "Password changed"}


@router.get("/{user_id}", response_model=UserResponse)
def get_user(user_id: int, db: Session = Depends(get_db), _user_id: int = Depends(get_current_user_id)):
    return svc_user.get_user_response(db, user_id)


@router.put("/{user_id}", response_model=UserResponse)
def update_user(
    user_id: int,
    data: UserUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user_id: int = Depends(get_current_user_id),
):
    result = svc_user.update_user(db, user_id, data, current_user_id)
    # Sync session locale when user changes their own preferred_locale
    if data.preferred_locale and user_id == current_user_id:
        request.session["locale"] = data.preferred_locale
    return result


@router.delete("/{user_id}", status_code=204)
def delete_user(user_id: int, db: Session = Depends(get_db), current_user_id: int = Depends(require_admin)):
    svc_user.delete_user(db, user_id, current_user_id)


@router.put("/{user_id}/password")
def reset_password(
    user_id: int, data: PasswordReset, db: Session = Depends(get_db), _user_id: int = Depends(require_admin)
):
    svc_user.reset_password(db, user_id, data.new_password)
    return {"detail": "Password reset"}


@router.post("/{user_id}/unlock")
def unlock_user(user_id: int, db: Session = Depends(get_db), _user_id: int = Depends(require_admin)):
    svc_user.unlock_user(db, user_id)
    return {"detail": "Account unlocked"}


class UserRoleAssign(BaseModel):
    role_id: int


@router.get("/{user_id}/roles", response_model=List[RoleResponse])
def list_user_roles(
    user_id: int,
    db: Session = Depends(get_db),
    _: int = Depends(require_admin),
):
    roles = crud_role.get_user_roles(db, user_id)
    return [crud_role.build_role_response(db, r) for r in roles]


@router.post("/{user_id}/roles")
def assign_user_role(
    user_id: int,
    data: UserRoleAssign,
    db: Session = Depends(get_db),
    _: int = Depends(require_admin),
):
    role = crud_role.get_role(db, data.role_id)
    if not role:
        raise NotFoundError(f"Role {data.role_id} not found")
    crud_role.assign_user_role(db, user_id, data.role_id)
    db.commit()
    return {"detail": "Role assigned"}


@router.delete("/{user_id}/roles/{role_id}", status_code=204)
def revoke_user_role(
    user_id: int,
    role_id: int,
    db: Session = Depends(get_db),
    _: int = Depends(require_admin),
):
    removed = crud_role.revoke_user_role(db, user_id, role_id)
    if not removed:
        raise NotFoundError(f"Role {role_id} not assigned to user {user_id}")
    db.commit()
