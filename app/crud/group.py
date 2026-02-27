from typing import List, Optional

from sqlalchemy.orm import Session

from app.models.group import Group
from portal_core.crud.base import CRUDBase

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
    """Return member count for a group.

    Users no longer have a group_id column (renamed to department_id → departments).
    Group membership at the user level is no longer tracked.
    """
    return 0
