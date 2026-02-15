from datetime import date
from typing import List, Optional

from sqlalchemy.orm import Session

from app.models.daily_report import DailyReport
from app.schemas.daily_report import DailyReportCreate, DailyReportUpdate


def get_report(db: Session, report_id: int) -> Optional[DailyReport]:
    return db.query(DailyReport).filter(DailyReport.id == report_id).first()


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
    report = DailyReport(user_id=user_id, **data.model_dump())
    db.add(report)
    db.commit()
    db.refresh(report)
    return report


def update_report(db: Session, report: DailyReport, data: DailyReportUpdate) -> DailyReport:
    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(report, key, value)
    db.commit()
    db.refresh(report)
    return report


def delete_report(db: Session, report: DailyReport) -> None:
    db.delete(report)
    db.commit()


def get_reports_by_date_range(db: Session, start_date: date, end_date: date) -> List[DailyReport]:
    return (
        db.query(DailyReport)
        .filter(DailyReport.report_date >= start_date, DailyReport.report_date <= end_date)
        .order_by(DailyReport.report_date.desc())
        .all()
    )
