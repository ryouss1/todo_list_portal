from typing import List, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from portal_core.crud.base import CRUDBase
from portal_core.models.department import Department

_crud = CRUDBase(Department)

get_department = _crud.get


def get_departments(db: Session) -> List[Department]:
    return db.query(Department).order_by(Department.sort_order, Department.name).all()


def get_departments_active(db: Session) -> List[Department]:
    """is_active=True の部門のみ返す（ツリー表示用）"""
    return (
        db.query(Department)
        .filter(Department.is_active.is_(True))
        .order_by(Department.sort_order, Department.name)
        .all()
    )


def create_department(
    db: Session,
    name: str,
    code: Optional[str] = None,
    description: Optional[str] = None,
    parent_id: Optional[int] = None,
    sort_order: int = 0,
    is_active: bool = True,
) -> Department:
    return _crud.create(
        db,
        {
            "name": name,
            "code": code,
            "description": description,
            "parent_id": parent_id,
            "sort_order": sort_order,
            "is_active": is_active,
        },
    )


def update_department(db: Session, dept: Department, data: dict) -> Department:
    for key, value in data.items():
        if value is not None:
            setattr(dept, key, value)
    db.flush()
    return dept


delete_department = _crud.delete


def count_members(db: Session, department_id: int) -> int:
    """department_id を持つ User の数を返す。カラムが未追加の場合は 0 を返す。"""
    from portal_core.models.user import User

    if not hasattr(User, "department_id"):
        return 0
    return db.query(func.count(User.id)).filter(User.department_id == department_id).scalar() or 0
