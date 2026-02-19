from typing import List, Optional

from sqlalchemy.orm import Session

from app.crud.base import CRUDBase
from app.models.group import Group
from app.models.user import User

_crud = CRUDBase(Group)

get_group = _crud.get


def get_groups(db: Session) -> List[Group]:
    return db.query(Group).order_by(Group.sort_order).all()


def create_group(db: Session, name: str, description: Optional[str] = None, sort_order: int = 0) -> Group:
    return _crud.create(db, {"name": name, "description": description, "sort_order": sort_order})


def update_group(db: Session, group: Group, data: dict) -> Group:
    return _crud.update(db, group, data)


delete_group = _crud.delete


def count_members(db: Session, group_id: int) -> int:
    return db.query(User).filter(User.group_id == group_id).count()
