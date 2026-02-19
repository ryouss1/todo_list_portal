from typing import List

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.config import API_ALERT_LIMIT
from app.core.deps import get_current_user_id, require_admin
from app.database import get_db
from app.schemas.alert import AlertCountResponse, AlertCreate, AlertResponse
from app.services import alert_service as svc

router = APIRouter(prefix="/api/alerts", tags=["alerts"])


@router.get("/", response_model=List[AlertResponse])
def list_alerts(
    active_only: bool = Query(False),
    limit: int = Query(API_ALERT_LIMIT),
    db: Session = Depends(get_db),
    _user_id: int = Depends(get_current_user_id),
):
    return svc.list_alerts(db, active_only=active_only, limit=limit)


@router.get("/count", response_model=AlertCountResponse)
def unacknowledged_count(
    db: Session = Depends(get_db),
    _user_id: int = Depends(get_current_user_id),
):
    return AlertCountResponse(count=svc.count_unacknowledged(db))


@router.post("/", response_model=AlertResponse, status_code=201)
async def create_alert(
    data: AlertCreate,
    db: Session = Depends(get_db),
    _user_id: int = Depends(get_current_user_id),
):
    return await svc.create_alert(db, data)


@router.get("/{alert_id}", response_model=AlertResponse)
def get_alert(
    alert_id: int,
    db: Session = Depends(get_db),
    _user_id: int = Depends(get_current_user_id),
):
    return svc.get_alert(db, alert_id)


@router.patch("/{alert_id}/acknowledge", response_model=AlertResponse)
def acknowledge_alert(
    alert_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    return svc.acknowledge_alert(db, alert_id, user_id)


@router.patch("/{alert_id}/deactivate", response_model=AlertResponse)
def deactivate_alert(
    alert_id: int,
    db: Session = Depends(get_db),
    _user_id: int = Depends(get_current_user_id),
):
    return svc.deactivate_alert(db, alert_id)


@router.delete("/{alert_id}", status_code=204)
def delete_alert(
    alert_id: int,
    db: Session = Depends(get_db),
    _user_id: int = Depends(require_admin),
):
    svc.delete_alert(db, alert_id)
