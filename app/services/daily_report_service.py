import logging
from datetime import date
from typing import Any, List, Optional

from sqlalchemy.orm import Session

from app.config import DEFAULT_TASK_CATEGORY_ID
from app.core.exceptions import NotFoundError
from app.core.utils import seconds_to_hm
from app.crud import daily_report as crud_report
from app.models.daily_report import DailyReport
from app.schemas.daily_report import DailyReportCreate, DailyReportUpdate

logger = logging.getLogger("app.services.daily_report")


def list_my_reports(db: Session, user_id: int, report_date: Optional[date] = None) -> List[DailyReport]:
    logger.info("Listing reports for user_id=%d, date=%s", user_id, report_date)
    return crud_report.get_reports_by_user(db, user_id, report_date=report_date)


def list_all_reports(db: Session, report_date: Optional[date] = None) -> List[DailyReport]:
    logger.info("Listing all reports, date=%s", report_date)
    return crud_report.get_all_reports(db, report_date=report_date)


def get_report(db: Session, report_id: int) -> DailyReport:
    """Get report by ID - all authenticated users can view any report."""
    report = crud_report.get_report(db, report_id)
    if not report:
        raise NotFoundError("Report not found")
    return report


def get_own_report(db: Session, report_id: int, user_id: int) -> DailyReport:
    """Get report by ID - only owner can access (for edit/delete)."""
    report = crud_report.get_report(db, report_id)
    if not report or report.user_id != user_id:
        raise NotFoundError("Report not found")
    return report


def create_report(db: Session, user_id: int, data: DailyReportCreate) -> DailyReport:
    logger.info("Creating report: user_id=%d, date=%s", user_id, data.report_date)
    report = crud_report.create_report(db, user_id, data)
    logger.info("Report created: id=%d", report.id)
    return report


def update_report(db: Session, report_id: int, user_id: int, data: DailyReportUpdate) -> DailyReport:
    report = get_own_report(db, report_id, user_id)
    logger.info("Updating report: id=%d", report_id)
    return crud_report.update_report(db, report, data)


def delete_report(db: Session, report_id: int, user_id: int) -> None:
    report = get_own_report(db, report_id, user_id)
    crud_report.delete_report(db, report)
    logger.info("Report deleted: id=%d", report_id)


def create_report_from_task(db: Session, task: Any, user_id: int, report_date: date) -> DailyReport:
    """Hook: create a DailyReport from a completed Task (flush-only, no standalone commit).

    Registered in main.py via task_service.register_on_task_done().
    """
    time_min = task.total_seconds // 60
    hours, mins = seconds_to_hm(task.total_seconds)
    time_str = f"{hours}h {mins}m" if task.total_seconds > 0 else ""
    work_content = task.title
    if time_str:
        work_content += f" ({time_str})"
    if task.description:
        work_content += f"\n{task.description}"
    data = DailyReportCreate(
        report_date=report_date,
        category_id=task.category_id or DEFAULT_TASK_CATEGORY_ID,
        task_name=task.title,
        backlog_ticket_id=task.backlog_ticket_id,
        time_minutes=time_min,
        work_content=work_content,
    )
    report = DailyReport(user_id=user_id, **data.model_dump())
    db.add(report)
    db.flush()
    logger.info("Report created from task: task_id=%s, date=%s", getattr(task, "id", "?"), report_date)
    return report
