from typing import Dict, List, Optional

from sqlalchemy.orm import Session

from app.crud.base import CRUDBase
from app.models.task_list_item import TaskListItem
from app.schemas.task_list_item import TaskListItemCreate, TaskListItemUpdate

_crud = CRUDBase(TaskListItem)

get_item = _crud.get


def get_unassigned_items(db: Session) -> List[TaskListItem]:
    return (
        db.query(TaskListItem)
        .filter(TaskListItem.assignee_id.is_(None))
        .order_by(TaskListItem.scheduled_date.asc().nullslast(), TaskListItem.created_at.asc())
        .all()
    )


def get_all_items(
    db: Session,
    assignee_id: Optional[int] = None,
    statuses: Optional[List[str]] = None,
    q: Optional[str] = None,
) -> List[TaskListItem]:
    query = db.query(TaskListItem)
    if assignee_id is not None:
        if assignee_id == 0:
            query = query.filter(TaskListItem.assignee_id.is_(None))
        else:
            query = query.filter(TaskListItem.assignee_id == assignee_id)
    if statuses:
        query = query.filter(TaskListItem.status.in_(statuses))
    if q:
        query = query.filter(TaskListItem.title.ilike(f"%{q}%"))
    return query.order_by(TaskListItem.scheduled_date.asc().nullslast(), TaskListItem.created_at.asc()).all()


def get_assigned_items(db: Session, user_id: int, statuses: Optional[List[str]] = None) -> List[TaskListItem]:
    q = db.query(TaskListItem).filter(TaskListItem.assignee_id == user_id)
    if statuses:
        q = q.filter(TaskListItem.status.in_(statuses))
    return q.order_by(TaskListItem.scheduled_date.asc().nullslast(), TaskListItem.created_at.asc()).all()


def create_item(db: Session, created_by: int, data: TaskListItemCreate) -> TaskListItem:
    return _crud.create(db, data, created_by=created_by)


def update_item(db: Session, item: TaskListItem, data: TaskListItemUpdate) -> TaskListItem:
    return _crud.update(db, item, data)


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


delete_item = _crud.delete


def get_item_for_update(db: Session, item_id: int) -> Optional[TaskListItem]:
    """Get a task list item with SELECT FOR UPDATE row lock."""
    return db.query(TaskListItem).filter(TaskListItem.id == item_id).with_for_update().first()


def get_items_by_ids(db: Session, item_ids: List[int]) -> Dict[int, TaskListItem]:
    """Batch-fetch task list items by IDs. Returns {item_id: item}."""
    if not item_ids:
        return {}
    items = db.query(TaskListItem).filter(TaskListItem.id.in_(item_ids)).all()
    return {item.id: item for item in items}


def accumulate_seconds(db: Session, item: TaskListItem, seconds: int) -> TaskListItem:
    item.total_seconds += seconds
    db.commit()
    db.refresh(item)
    return item
