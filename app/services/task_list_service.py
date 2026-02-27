import logging
from typing import List, Optional

from sqlalchemy.orm import Session

from app.constants import ItemStatus
from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError
from app.crud import task as crud_task
from app.crud import task_list_item as crud_tli
from app.models.task import Task
from app.models.task_list_item import TaskListItem
from app.schemas.task_list_item import TaskListItemCreate, TaskListItemUpdate
from app.services import task_service as svc_task

logger = logging.getLogger("app.services.task_list")


def _get_visible_item(db: Session, item_id: int, user_id: int) -> TaskListItem:
    """Get an item if the user can see it (unassigned, or assigned/created by user)."""
    item = crud_tli.get_item(db, item_id)
    if not item:
        raise NotFoundError("Item not found")
    if item.assignee_id is not None and item.assignee_id != user_id and item.created_by != user_id:
        raise NotFoundError("Item not found")
    return item


def _check_edit_permission(item: TaskListItem, user_id: int) -> None:
    """Only assignee or creator can edit."""
    if item.assignee_id is not None and item.assignee_id != user_id and item.created_by != user_id:
        raise ForbiddenError("No permission to edit this item")
    if item.assignee_id is None and item.created_by != user_id:
        raise ForbiddenError("No permission to edit this item")


def list_unassigned(db: Session) -> List[TaskListItem]:
    return crud_tli.get_unassigned_items(db)


def list_all(
    db: Session,
    assignee_id: Optional[int] = None,
    statuses: Optional[List[str]] = None,
    q: Optional[str] = None,
) -> List[TaskListItem]:
    return crud_tli.get_all_items(db, assignee_id, statuses, q)


def list_mine(db: Session, user_id: int, statuses: Optional[List[str]] = None) -> List[TaskListItem]:
    return crud_tli.get_assigned_items(db, user_id, statuses)


def get_item(db: Session, item_id: int, user_id: int) -> TaskListItem:
    return _get_visible_item(db, item_id, user_id)


def create_item(db: Session, user_id: int, data: TaskListItemCreate) -> TaskListItem:
    logger.info("Creating task list item: title=%s, user=%d", data.title, user_id)
    return crud_tli.create_item(db, user_id, data)


def update_item(db: Session, item_id: int, user_id: int, data: TaskListItemUpdate) -> TaskListItem:
    item = _get_visible_item(db, item_id, user_id)
    _check_edit_permission(item, user_id)
    logger.info("Updating task list item: id=%d", item_id)
    return crud_tli.update_item(db, item, data)


def delete_item(db: Session, item_id: int, user_id: int) -> None:
    item = _get_visible_item(db, item_id, user_id)
    _check_edit_permission(item, user_id)
    crud_tli.delete_item(db, item)
    logger.info("Deleted task list item: id=%d", item_id)


def assign_to_me(db: Session, item_id: int, user_id: int) -> TaskListItem:
    item = crud_tli.get_item(db, item_id)
    if not item:
        raise NotFoundError("Item not found")
    if item.assignee_id is not None and item.assignee_id != user_id:
        raise ForbiddenError("Item is already assigned to another user")
    logger.info("Assigning item %d to user %d", item_id, user_id)
    return crud_tli.assign_item(db, item, user_id)


def unassign_item(db: Session, item_id: int, user_id: int) -> TaskListItem:
    item = _get_visible_item(db, item_id, user_id)
    _check_edit_permission(item, user_id)
    if item.status == ItemStatus.IN_PROGRESS:
        raise ForbiddenError("Cannot unassign an in-progress item")
    logger.info("Unassigning item %d", item_id)
    return crud_tli.unassign_item(db, item)


def start_as_task(db: Session, item_id: int, user_id: int) -> Task:
    """Copy a TaskListItem to a new Task, start its timer, and set item status to in_progress."""
    # Lock the row to prevent concurrent start_as_task() calls from creating duplicate tasks.
    item = crud_tli.get_item_for_update(db, item_id)
    if not item:
        raise NotFoundError("Item not found")
    if item.assignee_id is not None and item.assignee_id != user_id and item.created_by != user_id:
        raise NotFoundError("Item not found")
    if item.status != ItemStatus.OPEN:
        raise ConflictError("Item is already started")

    # DB-level duplicate check: prevent multiple Tasks for the same item
    existing_count = crud_task.count_by_source_item_id(db, item.id)
    if existing_count > 0:
        raise ConflictError("A task already exists for this item")

    task = svc_task.create_and_start_task(
        db,
        user_id=user_id,
        title=item.title,
        description=item.description,
        category_id=item.category_id,
        backlog_ticket_id=item.backlog_ticket_id,
        source_item_id=item.id,
    )

    item.status = ItemStatus.IN_PROGRESS
    if item.assignee_id is None:
        item.assignee_id = user_id
    db.commit()
    db.refresh(task)
    logger.info("Started task %d from item %d (timer auto-started)", task.id, item_id)
    return task
