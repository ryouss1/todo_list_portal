from datetime import datetime, timezone
from typing import Dict, List, Optional

from sqlalchemy.orm import Session

from app.constants import TaskStatus
from app.crud.base import CRUDBase
from app.models.task import Task
from app.models.task_time_entry import TaskTimeEntry
from app.schemas.task import TaskCreate, TaskUpdate

_crud = CRUDBase(Task)

get_task = _crud.get


def get_task_for_update(db: Session, task_id: int) -> Optional[Task]:
    """Get task with SELECT FOR UPDATE row lock (prevents TOCTOU in timer ops)."""
    return db.query(Task).filter(Task.id == task_id).with_for_update().first()


def get_tasks(db: Session, user_id: int) -> List[Task]:
    return db.query(Task).filter(Task.user_id == user_id).order_by(Task.created_at.desc()).all()


def create_task(db: Session, user_id: int, data: TaskCreate) -> Task:
    return _crud.create(db, data, user_id=user_id)


def update_task(db: Session, task: Task, data: TaskUpdate) -> Task:
    return _crud.update(db, task, data)


delete_task = _crud.delete


def start_timer(db: Session, task: Task) -> TaskTimeEntry:
    task.status = TaskStatus.IN_PROGRESS
    entry = TaskTimeEntry(
        task_id=task.id,
        started_at=datetime.now(timezone.utc),
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    db.refresh(task)
    return entry


def stop_timer(db: Session, task: Task) -> Optional[TaskTimeEntry]:
    entry = db.query(TaskTimeEntry).filter(TaskTimeEntry.task_id == task.id, TaskTimeEntry.stopped_at.is_(None)).first()
    if not entry:
        return None

    now = datetime.now(timezone.utc)
    entry.stopped_at = now
    elapsed = int((now - entry.started_at).total_seconds())
    entry.elapsed_seconds = elapsed
    task.total_seconds += elapsed
    task.status = TaskStatus.PENDING
    db.commit()
    db.refresh(entry)
    db.refresh(task)
    return entry


def get_time_entries(db: Session, task_id: int) -> List[TaskTimeEntry]:
    return (
        db.query(TaskTimeEntry).filter(TaskTimeEntry.task_id == task_id).order_by(TaskTimeEntry.started_at.desc()).all()
    )


def get_active_entry(db: Session, task_id: int) -> Optional[TaskTimeEntry]:
    return db.query(TaskTimeEntry).filter(TaskTimeEntry.task_id == task_id, TaskTimeEntry.stopped_at.is_(None)).first()


def count_by_source_item_id(db: Session, source_item_id: int) -> int:
    return db.query(Task).filter(Task.source_item_id == source_item_id).count()


def get_in_progress_with_backlog(db: Session) -> List[Task]:
    """Get all in-progress tasks that have a backlog ticket ID (for presence display)."""
    return db.query(Task).filter(Task.status == TaskStatus.IN_PROGRESS, Task.backlog_ticket_id.isnot(None)).all()


def get_tasks_by_ids(db: Session, task_ids: List[int]) -> List[Task]:
    """Batch-fetch tasks by IDs."""
    if not task_ids:
        return []
    return db.query(Task).filter(Task.id.in_(task_ids)).all()


def get_active_entries_batch(db: Session, task_ids: List[int]) -> Dict[int, TaskTimeEntry]:
    """Return {task_id: active_entry} for all specified tasks in a single query."""
    if not task_ids:
        return {}
    entries = (
        db.query(TaskTimeEntry).filter(TaskTimeEntry.task_id.in_(task_ids), TaskTimeEntry.stopped_at.is_(None)).all()
    )
    return {e.task_id: e for e in entries}


def stop_timer_at(db: Session, task: Task, end_time_utc: datetime) -> Optional[TaskTimeEntry]:
    """Stop the active timer at a specified UTC time (flush only, no commit)."""
    entry = db.query(TaskTimeEntry).filter(TaskTimeEntry.task_id == task.id, TaskTimeEntry.stopped_at.is_(None)).first()
    if not entry:
        return None
    entry.stopped_at = end_time_utc
    elapsed = max(0, int((end_time_utc - entry.started_at).total_seconds()))
    entry.elapsed_seconds = elapsed
    task.total_seconds += elapsed
    task.status = TaskStatus.PENDING
    db.flush()
    return entry
