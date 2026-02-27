from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from portal_core.core.deps import get_current_user_id, require_admin
from portal_core.database import get_db
from portal_core.schemas.department import DepartmentCreate, DepartmentResponse, DepartmentUpdate
from portal_core.services.department_service import (
    create_department_svc,
    delete_department_svc,
    get_departments_active_svc,
    get_departments_svc,
    update_department_svc,
)

router = APIRouter(prefix="/api/departments", tags=["departments"])


def _to_response(dept) -> DepartmentResponse:
    return DepartmentResponse(
        id=dept.id,
        name=dept.name,
        code=dept.code,
        description=dept.description,
        parent_id=dept.parent_id,
        sort_order=dept.sort_order,
        is_active=dept.is_active,
        member_count=0,
        created_at=dept.created_at,
        updated_at=dept.updated_at,
    )


@router.get("/tree", response_model=List[DepartmentResponse])
def get_departments_tree(db: Session = Depends(get_db), _user_id: int = Depends(get_current_user_id)):
    depts = get_departments_active_svc(db)
    return [_to_response(d) for d in depts]


@router.get("/", response_model=List[DepartmentResponse])
def list_departments(db: Session = Depends(get_db), _user_id: int = Depends(get_current_user_id)):
    depts = get_departments_svc(db)
    return [_to_response(d) for d in depts]


@router.post("/", response_model=DepartmentResponse, status_code=201)
def create_department(
    data: DepartmentCreate,
    db: Session = Depends(get_db),
    _user_id: int = Depends(require_admin),
):
    dept = create_department_svc(db, data)
    db.commit()
    db.refresh(dept)
    return _to_response(dept)


@router.put("/{dept_id}", response_model=DepartmentResponse)
def update_department(
    dept_id: int,
    data: DepartmentUpdate,
    db: Session = Depends(get_db),
    _user_id: int = Depends(require_admin),
):
    dept = update_department_svc(db, dept_id, data)
    db.commit()
    db.refresh(dept)
    return _to_response(dept)


@router.delete("/{dept_id}", status_code=204)
def delete_department(
    dept_id: int,
    db: Session = Depends(get_db),
    _user_id: int = Depends(require_admin),
):
    delete_department_svc(db, dept_id)
    db.commit()
