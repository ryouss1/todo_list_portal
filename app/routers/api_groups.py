from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.schemas.group import GroupCreate, GroupResponse, GroupUpdate
from app.services import group_service as svc_group
from portal_core.core.deps import get_current_user_id, require_admin
from portal_core.database import get_db

router = APIRouter(prefix="/api/groups", tags=["groups"])


@router.get("/", response_model=List[GroupResponse])
def list_groups(db: Session = Depends(get_db), _user_id: int = Depends(get_current_user_id)):
    return svc_group.list_groups(db)


@router.post("/", response_model=GroupResponse, status_code=201)
def create_group(data: GroupCreate, db: Session = Depends(get_db), _user_id: int = Depends(require_admin)):
    return svc_group.create_group(db, data)


@router.put("/{group_id}", response_model=GroupResponse)
def update_group(
    group_id: int, data: GroupUpdate, db: Session = Depends(get_db), _user_id: int = Depends(require_admin)
):
    return svc_group.update_group(db, group_id, data)


@router.delete("/{group_id}", status_code=204)
def delete_group(group_id: int, db: Session = Depends(get_db), _user_id: int = Depends(require_admin)):
    svc_group.delete_group(db, group_id)
