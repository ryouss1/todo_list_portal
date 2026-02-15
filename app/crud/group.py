from typing import List, Optional

from sqlalchemy.orm import Session

from app.models.group import Group
from app.models.user import User


def get_group(db: Session, group_id: int) -> Optional[Group]:
    return db.query(Group).filter(Group.id == group_id).first()


def get_groups(db: Session) -> List[Group]:
    return db.query(Group).order_by(Group.sort_order).all()


def create_group(db: Session, name: str, description: Optional[str] = None, sort_order: int = 0) -> Group:
    group = Group(name=name, description=description, sort_order=sort_order)
    db.add(group)
    db.commit()
    db.refresh(group)
    return group


def update_group(db: Session, group: Group, data: dict) -> Group:
    for key, value in data.items():
        setattr(group, key, value)
    db.commit()
    db.refresh(group)
    return group


def delete_group(db: Session, group: Group) -> None:
    db.delete(group)
    db.commit()


def count_members(db: Session, group_id: int) -> int:
    return db.query(User).filter(User.group_id == group_id).count()
