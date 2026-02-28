"""CRUD operations for wiki task links."""

from typing import List, Optional, Tuple

from sqlalchemy import delete, insert, select
from sqlalchemy.orm import Session

from app.models.task import Task
from app.models.task_list_item import TaskListItem
from app.models.user import User
from app.models.wiki_task_link import WikiPageTask, wiki_page_task_items


def get_task_links(db: Session, page_id: int) -> Tuple[list, list]:
    """Return (task_items_rows, tasks_rows) for a page."""
    task_items_rows = db.execute(
        select(
            TaskListItem.id,
            TaskListItem.title,
            TaskListItem.status,
            TaskListItem.assignee_id,
            User.display_name.label("assignee_name"),
            TaskListItem.backlog_ticket_id,
            TaskListItem.scheduled_date,
            wiki_page_task_items.c.linked_at,
        )
        .join(wiki_page_task_items, TaskListItem.id == wiki_page_task_items.c.task_item_id)
        .outerjoin(User, TaskListItem.assignee_id == User.id)
        .where(wiki_page_task_items.c.page_id == page_id)
        .order_by(wiki_page_task_items.c.linked_at.desc())
    ).fetchall()

    tasks_rows = db.execute(
        select(
            WikiPageTask.id.label("link_id"),
            WikiPageTask.task_id,
            WikiPageTask.task_title,
            Task.status,
            Task.user_id,
            User.display_name,
            Task.backlog_ticket_id,
            WikiPageTask.linked_at,
        )
        .where(WikiPageTask.page_id == page_id)
        .outerjoin(Task, WikiPageTask.task_id == Task.id)
        .outerjoin(User, Task.user_id == User.id)
        .order_by(WikiPageTask.linked_at.desc())
    ).fetchall()

    return task_items_rows, tasks_rows


def update_task_item_links(db: Session, page_id: int, task_item_ids: List[int], linked_by: int) -> None:
    """Bulk-update task_list_item links (diff update)."""
    current = {
        row[0]
        for row in db.execute(
            select(wiki_page_task_items.c.task_item_id).where(wiki_page_task_items.c.page_id == page_id)
        ).fetchall()
    }
    new_set = set(task_item_ids)

    to_remove = current - new_set
    if to_remove:
        db.execute(
            delete(wiki_page_task_items).where(
                wiki_page_task_items.c.page_id == page_id,
                wiki_page_task_items.c.task_item_id.in_(to_remove),
            )
        )

    to_add = new_set - current
    if to_add:
        db.execute(
            insert(wiki_page_task_items).values(
                [{"page_id": page_id, "task_item_id": tid, "linked_by": linked_by} for tid in to_add]
            )
        )


def add_task_link(db: Session, page_id: int, task_id: int, linked_by: int) -> Optional[bool]:
    """Link an active task to a wiki page.

    Returns:
        None  — task not found
        True  — already linked (no-op)
        False — newly linked
    """
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        return None
    existing = db.query(WikiPageTask).filter(WikiPageTask.page_id == page_id, WikiPageTask.task_id == task_id).first()
    if existing:
        return True
    link = WikiPageTask(
        page_id=page_id,
        task_id=task_id,
        task_title=task.title,
        linked_by=linked_by,
    )
    db.add(link)
    return False


def remove_task_link(db: Session, page_id: int, task_id: int) -> bool:
    """Remove an active task link. Returns True if removed."""
    link = db.query(WikiPageTask).filter(WikiPageTask.page_id == page_id, WikiPageTask.task_id == task_id).first()
    if not link:
        return False
    db.delete(link)
    return True


def get_linked_task_item_ids(db: Session, page_id: int) -> List[int]:
    rows = db.execute(
        select(wiki_page_task_items.c.task_item_id).where(wiki_page_task_items.c.page_id == page_id)
    ).fetchall()
    return [r[0] for r in rows]
