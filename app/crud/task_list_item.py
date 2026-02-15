from typing import List, Optional

from sqlalchemy.orm import Session

from app.models.task_list_item import TaskListItem
from app.schemas.task_list_item import TaskListItemCreate, TaskListItemUpdate


def get_item(db: Session, item_id: int) -> Optional[TaskListItem]:
    return db.query(TaskListItem).filter(TaskListItem.id == item_id).first()


def get_unassigned_items(db: Session) -> List[TaskListItem]:
    return (
        db.query(TaskListItem)
        .filter(TaskListItem.assignee_id.is_(None))
        .order_by(TaskListItem.scheduled_date.asc().nullslast(), TaskListItem.created_at.asc())
        .all()
    )


def get_all_items(db: Session, assignee_id: Optional[int] = None) -> List[TaskListItem]:
    q = db.query(TaskListItem)
    if assignee_id is not None:
        if assignee_id == 0:
            q = q.filter(TaskListItem.assignee_id.is_(None))
        else:
            q = q.filter(TaskListItem.assignee_id == assignee_id)
    return q.order_by(TaskListItem.scheduled_date.asc().nullslast(), TaskListItem.created_at.asc()).all()


def get_assigned_items(db: Session, user_id: int) -> List[TaskListItem]:
    return (
        db.query(TaskListItem)
        .filter(TaskListItem.assignee_id == user_id)
        .order_by(TaskListItem.scheduled_date.asc().nullslast(), TaskListItem.created_at.asc())
        .all()
    )


def create_item(db: Session, created_by: int, data: TaskListItemCreate) -> TaskListItem:
    item_data = data.model_dump()
    item = TaskListItem(created_by=created_by, **item_data)
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def update_item(db: Session, item: TaskListItem, data: TaskListItemUpdate) -> TaskListItem:
    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(item, key, value)
    db.commit()
    db.refresh(item)
    return item


def assign_item(db: Session, item: TaskListItem, user_id: int) -> TaskListItem:
    item.assignee_id = user_id
    db.commit()
    db.refresh(item)
    return item


def unassign_item(db: Session, item: TaskListItem) -> TaskListItem:
    item.assignee_id = None
    db.commit()
    db.refresh(item)
    return item


def delete_item(db: Session, item: TaskListItem) -> None:
    db.delete(item)
    db.commit()


def accumulate_seconds(db: Session, item: TaskListItem, seconds: int) -> TaskListItem:
    item.total_seconds += seconds
    db.commit()
    db.refresh(item)
    return item
