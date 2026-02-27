import logging
from typing import List

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from portal_core.core.exceptions import ConflictError, NotFoundError
from portal_core.crud import department as crud_dept
from portal_core.models.department import Department
from portal_core.schemas.department import DepartmentCreate, DepartmentUpdate

logger = logging.getLogger("portal_core.services.department")


def get_departments_svc(db: Session) -> List[Department]:
    return crud_dept.get_departments(db)


def get_departments_active_svc(db: Session) -> List[Department]:
    return crud_dept.get_departments_active(db)


def get_department_svc(db: Session, dept_id: int):
    dept = crud_dept.get_department(db, dept_id)
    if not dept:
        raise NotFoundError("Department not found")
    return dept


def create_department_svc(db: Session, data: DepartmentCreate):
    logger.info("Creating department: name=%s", data.name)
    try:
        dept = crud_dept.create_department(
            db,
            name=data.name,
            code=data.code,
            description=data.description,
            parent_id=data.parent_id,
            sort_order=data.sort_order,
            is_active=data.is_active,
        )
    except IntegrityError:
        db.rollback()
        raise ConflictError("Department name already exists")
    logger.info("Department created: id=%d", dept.id)
    return dept


def update_department_svc(db: Session, dept_id: int, data: DepartmentUpdate):
    dept = get_department_svc(db, dept_id)
    update_data = data.model_dump(exclude_unset=True)
    if not update_data:
        return dept
    try:
        dept = crud_dept.update_department(db, dept, update_data)
    except IntegrityError:
        db.rollback()
        raise ConflictError("Department name already exists")
    logger.info("Department updated: id=%d", dept_id)
    return dept


def delete_department_svc(db: Session, dept_id: int) -> None:
    dept = get_department_svc(db, dept_id)
    crud_dept.delete_department(db, dept)
    logger.info("Department deleted: id=%d", dept_id)
