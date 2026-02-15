from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.deps import get_current_user_id
from app.database import get_db
from app.schemas.summary import BusinessSummaryResponse
from app.services import summary_service as svc_summary

router = APIRouter(prefix="/api/summary", tags=["summary"])


@router.get("/", response_model=BusinessSummaryResponse)
def get_summary(
    period: str = Query("weekly", pattern="^(daily|weekly|monthly)$"),
    ref_date: Optional[date] = None,
    group_id: Optional[int] = None,
    db: Session = Depends(get_db),
    _user_id: int = Depends(get_current_user_id),
):
    if ref_date is None:
        ref_date = date.today()
    return svc_summary.get_summary(db, period, ref_date, group_id=group_id)
