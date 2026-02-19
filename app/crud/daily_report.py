from datetime import date
from typing import List, Optional

from sqlalchemy.orm import Session

from app.crud.base import CRUDBase
from app.models.daily_report import DailyReport
from app.schemas.daily_report import DailyReportCreate, DailyReportUpdate

_crud = CRUDBase(DailyReport)

get_report = _crud.get


def get_reports_by_user(db: Session, user_id: int, report_date: Optional[date] = None) -> List[DailyReport]:
    q = db.query(DailyReport).filter(DailyReport.user_id == user_id)
    if report_date is not None:
        q = q.filter(DailyReport.report_date == report_date)
    return q.order_by(DailyReport.report_date.desc()).all()


def get_all_reports(db: Session, report_date: Optional[date] = None) -> List[DailyReport]:
    q = db.query(DailyReport)
    if report_date is not None:
        q = q.filter(DailyReport.report_date == report_date)
    return q.order_by(DailyReport.report_date.desc()).all()


def get_report_by_user_and_date(db: Session, user_id: int, report_date: date) -> Optional[DailyReport]:
    return db.query(DailyReport).filter(DailyReport.user_id == user_id, DailyReport.report_date == report_date).first()


def create_report(db: Session, user_id: int, data: DailyReportCreate) -> DailyReport:
    return _crud.create(db, data, user_id=user_id)


def update_report(db: Session, report: DailyReport, data: DailyReportUpdate) -> DailyReport:
    return _crud.update(db, report, data)


delete_report = _crud.delete


def get_reports_by_date_range(db: Session, start_date: date, end_date: date) -> List[DailyReport]:
    return (
        db.query(DailyReport)
        .filter(DailyReport.report_date >= start_date, DailyReport.report_date <= end_date)
        .order_by(DailyReport.report_date.desc())
        .all()
    )
