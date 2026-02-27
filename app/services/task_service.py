import logging
from datetime import date, datetime, timezone
from typing import Dict, List, Optional

from sqlalchemy.orm import Session

from app.config import DEFAULT_TASK_CATEGORY_ID
from app.constants import ItemStatus, TaskStatus
from app.core.exceptions import ConflictError, NotFoundError
from app.core.utils import parse_hhmm_to_utc, seconds_to_hm
from app.crud import daily_report as crud_report
from app.crud import task as crud_task
from app.crud import task_list_item as crud_tli
from app.models.daily_report import DailyReport
from app.models.task import Task
from app.models.task_time_entry import TaskTimeEntry
from app.schemas.daily_report import DailyReportCreate
from app.schemas.task import BatchDoneItem, BatchDoneResult, TaskCreate, TaskUpdate

logger = logging.getLogger("app.services.task")


def list_tasks(db: Session, user_id: int, limit: int = 200, offset: int = 0) -> List[Task]:
    logger.info("Listing tasks for user_id=%d", user_id)
    return crud_task.get_tasks(db, user_id, limit=limit, offset=offset)


def get_task(db: Session, task_id: int, user_id: int) -> Task:
    task = crud_task.get_task(db, task_id)
    if not task or task.user_id != user_id:
        logger.warning("Task not found: id=%d", task_id)
        raise NotFoundError("Task not found")
    return task


def create_task(db: Session, user_id: int, data: TaskCreate) -> Task:
    logger.info("Creating task: title=%s", data.title)
    task = crud_task.create_task(db, user_id, data)
    logger.info("Task created: id=%d", task.id)
    return task


def create_and_start_task(
    db: Session,
    user_id: int,
    title: str,
    description: Optional[str] = None,
    category_id: Optional[int] = None,
    backlog_ticket_id: Optional[str] = None,
    source_item_id: Optional[int] = None,
) -> Task:
    """Create a Task with status=in_progress and an active TaskTimeEntry (flush only)."""
    task = Task(
        user_id=user_id,
        title=title,
        description=description,
        category_id=category_id,
        backlog_ticket_id=backlog_ticket_id,
        source_item_id=source_item_id,
        status=TaskStatus.IN_PROGRESS,
    )
    db.add(task)
    db.flush()

    entry = TaskTimeEntry(
        task_id=task.id,
        started_at=datetime.now(timezone.utc),
    )
    db.add(entry)
    db.flush()

    logger.info("Created and started task: id=%d, title=%s", task.id, title)
    return task


def _sync_source_item_status(db: Session, source_item_id: int, flush_only: bool = False) -> None:
    """Reset source TaskListItem to 'open' if no linked Tasks remain.

    Items with status='done' are not reset (manual completion is preserved).
    """
    source_item = crud_tli.get_item(db, source_item_id)
    if not source_item:
        return
    if source_item.status == ItemStatus.DONE:
        return
    remaining = crud_task.count_by_source_item_id(db, source_item_id)
    if remaining == 0 and source_item.status == ItemStatus.IN_PROGRESS:
        source_item.status = ItemStatus.OPEN
        if flush_only:
            db.flush()
        else:
            db.commit()
        logger.info(
            "Reset source item %d status to open (no remaining tasks)",
            source_item_id,
        )


def update_task(db: Session, task_id: int, user_id: int, data: TaskUpdate) -> Task:
    task = get_task(db, task_id, user_id)
    logger.info("Updating task: id=%d", task_id)
    return crud_task.update_task(db, task, data)


def delete_task(db: Session, task_id: int, user_id: int) -> None:
    task = get_task(db, task_id, user_id)
    source_item_id = task.source_item_id
    crud_task.delete_task(db, task)
    if source_item_id:
        _sync_source_item_status(db, source_item_id)
    logger.info("Task deleted: id=%d", task_id)


def _get_task_with_lock(db: Session, task_id: int, user_id: int) -> Task:
    """Get task with SELECT FOR UPDATE, checking ownership.

    The row lock on `tasks` serializes concurrent timer operations:
    - Concurrent requests block at this SELECT FOR UPDATE until the first commits.
    - After unblocking, they read the latest committed state of task_time_entries
      (READ COMMITTED: each statement sees the latest committed data).
    - This prevents both duplicate start_timer entries and lost updates in stop_timer.
    """
    task = crud_task.get_task_for_update(db, task_id)
    if not task or task.user_id != user_id:
        logger.warning("Task not found (locked): id=%d", task_id)
        raise NotFoundError("Task not found")
    return task


def start_timer(db: Session, task_id: int, user_id: int) -> TaskTimeEntry:
    task = _get_task_with_lock(db, task_id, user_id)
    active = crud_task.get_active_entry(db, task_id)
    if active:
        logger.warning("Timer already running: task_id=%d", task_id)
        raise ConflictError("Timer already running")
    entry = crud_task.start_timer(db, task)
    logger.info("Timer started: task_id=%d, entry_id=%d", task_id, entry.id)
    return entry


def stop_timer(db: Session, task_id: int, user_id: int) -> TaskTimeEntry:
    task = _get_task_with_lock(db, task_id, user_id)
    entry = crud_task.stop_timer(db, task)
    if not entry:
        logger.warning("No active timer: task_id=%d", task_id)
        raise ConflictError("No active timer")
    logger.info("Timer stopped: task_id=%d, elapsed=%ds", task_id, entry.elapsed_seconds)
    return entry


def done_task(db: Session, task_id: int, user_id: int) -> Optional[DailyReport]:
    task = get_task(db, task_id, user_id)

    # Stop running timer if any
    active = crud_task.get_active_entry(db, task_id)
    if active:
        crud_task.stop_timer(db, task)

    # Create daily report if report flag is set
    report = None
    if task.report:
        data = _build_daily_report_data(task, date.today())
        report = crud_report.create_report(db, user_id, data)

    # Accumulate time to source TaskListItem if linked
    source_item_id = task.source_item_id
    accumulated_seconds = task.total_seconds

    # Delete task (CASCADE deletes time_entries)
    crud_task.delete_task(db, task)

    if source_item_id:
        if accumulated_seconds > 0:
            source_item = crud_tli.get_item(db, source_item_id)
            if source_item:
                crud_tli.accumulate_seconds(db, source_item, accumulated_seconds)
        _sync_source_item_status(db, source_item_id)

    logger.info("Task done: id=%d, report=%s", task_id, report is not None)
    return report


def get_time_entries(db: Session, task_id: int, user_id: int) -> List[TaskTimeEntry]:
    get_task(db, task_id, user_id)  # Validate task exists and belongs to user
    return crud_task.get_time_entries(db, task_id)


def _build_daily_report_data(task: Task, report_date: date) -> DailyReportCreate:
    """Build DailyReportCreate from a completed task (shared by done_task and batch_done)."""
    time_min = task.total_seconds // 60
    hours, mins = seconds_to_hm(task.total_seconds)
    time_str = f"{hours}h {mins}m" if task.total_seconds > 0 else ""
    work_content = task.title
    if time_str:
        work_content += f" ({time_str})"
    if task.description:
        work_content += f"\n{task.description}"
    return DailyReportCreate(
        report_date=report_date,
        category_id=task.category_id or DEFAULT_TASK_CATEGORY_ID,
        task_name=task.title,
        backlog_ticket_id=task.backlog_ticket_id,
        time_minutes=time_min,
        work_content=work_content,
    )


def _get_task_local_date(task: Task) -> date:
    """Return the local date of the task's updated_at (or created_at)."""
    dt = task.updated_at or task.created_at
    # Convert UTC datetime to local timezone
    local_dt = dt.astimezone()
    return local_dt.date()


def batch_done(db: Session, user_id: int, items: List[BatchDoneItem]) -> List[BatchDoneResult]:
    """Batch-complete overdue tasks with specified end times."""
    task_ids = [item.task_id for item in items]

    # Batch-fetch tasks and active entries (2 queries instead of 2N)
    task_map = {t.id: t for t in crud_task.get_tasks_by_ids(db, task_ids)}
    active_entries = crud_task.get_active_entries_batch(db, task_ids)

    # Ownership check upfront (before any DB writes)
    for item in items:
        t = task_map.get(item.task_id)
        if not t or t.user_id != user_id:
            raise NotFoundError(f"Task not found: {item.task_id}")

    results = []
    source_item_ids: set = set()
    accumulated_by_source: Dict[int, int] = {}

    for item in items:
        task = task_map[item.task_id]
        task_date = _get_task_local_date(task)
        end_time_utc = parse_hhmm_to_utc(task_date, item.end_time)

        # Stop running timer at specified time (dict lookup, no DB)
        if task.id in active_entries:
            crud_task.stop_timer_at(db, task, end_time_utc)

        # Create daily report if report flag is set
        report_id = None
        if task.report:
            data = _build_daily_report_data(task, task_date)
            # Use flush-only to avoid partial commits
            report = DailyReport(user_id=user_id, **data.model_dump())
            db.add(report)
            db.flush()
            report_id = report.id

        # Capture source info before delete
        source_item_id = task.source_item_id
        accumulated_seconds = task.total_seconds

        if source_item_id:
            source_item_ids.add(source_item_id)
            if accumulated_seconds > 0:
                accumulated_by_source[source_item_id] = (
                    accumulated_by_source.get(source_item_id, 0) + accumulated_seconds
                )

        # Delete task (CASCADE deletes time_entries)
        db.delete(task)
        db.flush()

        results.append(BatchDoneResult(task_id=item.task_id, report_id=report_id))

    # Batch-update source item seconds (1 query instead of N)
    if accumulated_by_source:
        source_items = crud_tli.get_items_by_ids(db, list(accumulated_by_source.keys()))
        for si in source_items.values():
            si.total_seconds += accumulated_by_source[si.id]
        db.flush()

    # Sync source item statuses before final commit
    for sid in source_item_ids:
        _sync_source_item_status(db, sid, flush_only=True)

    db.commit()
    logger.info("Batch done: %d tasks completed for user_id=%d", len(items), user_id)
    return results
