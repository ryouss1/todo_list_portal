from datetime import date
from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.deps import get_current_user_id
from app.database import get_db
from app.schemas.daily_report import DailyReportCreate, DailyReportResponse, DailyReportUpdate
from app.services import daily_report_service as svc_report

router = APIRouter(prefix="/api/reports", tags=["reports"])


@router.get("/", response_model=List[DailyReportResponse])
def list_my_reports(
    report_date: Optional[date] = Query(None),
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    return svc_report.list_my_reports(db, user_id, report_date=report_date)


@router.get("/all", response_model=List[DailyReportResponse])
def list_all_reports(
    report_date: Optional[date] = Query(None),
    db: Session = Depends(get_db),
    _user_id: int = Depends(get_current_user_id),
):
    return svc_report.list_all_reports(db, report_date=report_date)


@router.post("/", response_model=DailyReportResponse, status_code=201)
def create_report(data: DailyReportCreate, db: Session = Depends(get_db), user_id: int = Depends(get_current_user_id)):
    return svc_report.create_report(db, user_id, data)


@router.get("/{report_id}", response_model=DailyReportResponse)
def get_report(report_id: int, db: Session = Depends(get_db), _user_id: int = Depends(get_current_user_id)):
    return svc_report.get_report(db, report_id)


@router.put("/{report_id}", response_model=DailyReportResponse)
def update_report(
    report_id: int, data: DailyReportUpdate, db: Session = Depends(get_db), user_id: int = Depends(get_current_user_id)
):
    return svc_report.update_report(db, report_id, user_id, data)


@router.delete("/{report_id}", status_code=204)
def delete_report(report_id: int, db: Session = Depends(get_db), user_id: int = Depends(get_current_user_id)):
    svc_report.delete_report(db, report_id, user_id)
