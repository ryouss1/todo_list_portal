from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from portal_core.core.deps import require_admin
from portal_core.core.exceptions import DuplicateError, NotFoundError
from portal_core.crud import role as crud_role
from portal_core.database import get_db
from portal_core.schemas.role import PermissionItem, RoleCreate, RoleResponse, RoleUpdate

router = APIRouter(prefix="/api/roles", tags=["roles"])


@router.get("/", response_model=List[RoleResponse])
def list_roles(db: Session = Depends(get_db), _: int = Depends(require_admin)):
    return [crud_role.build_role_response(db, r) for r in crud_role.get_roles(db)]


@router.post("/", response_model=RoleResponse, status_code=201)
def create_role(
    data: RoleCreate,
    db: Session = Depends(get_db),
    _: int = Depends(require_admin),
):
    if crud_role.get_role_by_name(db, data.name):
        raise DuplicateError(f"Role '{data.name}' already exists")
    role = crud_role.create_role(db, data)
    db.commit()
    db.refresh(role)
    return crud_role.build_role_response(db, role)


@router.get("/{role_id}", response_model=RoleResponse)
def get_role(role_id: int, db: Session = Depends(get_db), _: int = Depends(require_admin)):
    role = crud_role.get_role(db, role_id)
    if not role:
        raise NotFoundError("Role not found")
    return crud_role.build_role_response(db, role)


@router.put("/{role_id}", response_model=RoleResponse)
def update_role(
    role_id: int,
    data: RoleUpdate,
    db: Session = Depends(get_db),
    _: int = Depends(require_admin),
):
    role = crud_role.update_role(db, role_id, data)
    if not role:
        raise NotFoundError("Role not found")
    db.commit()
    db.refresh(role)
    return crud_role.build_role_response(db, role)


@router.put("/{role_id}/permissions", response_model=RoleResponse)
def set_permissions(
    role_id: int,
    perms: List[PermissionItem],
    db: Session = Depends(get_db),
    _: int = Depends(require_admin),
):
    role = crud_role.get_role(db, role_id)
    if not role:
        raise NotFoundError("Role not found")
    crud_role.set_role_permissions(db, role_id, [(p.resource, p.action, p.kino_kbn) for p in perms])
    db.commit()
    db.refresh(role)
    return crud_role.build_role_response(db, role)


@router.delete("/{role_id}", status_code=204)
def delete_role(
    role_id: int,
    db: Session = Depends(get_db),
    _: int = Depends(require_admin),
):
    if not crud_role.get_role(db, role_id):
        raise NotFoundError("Role not found")
    crud_role.delete_role(db, role_id)
    db.commit()
