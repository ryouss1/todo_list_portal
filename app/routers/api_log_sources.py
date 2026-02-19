"""Log source management API (v2 with remote connections)."""

from typing import List, Optional

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.deps import get_current_user_id, require_admin
from app.database import get_db
from app.schemas.log_file import LogFileResponse
from app.schemas.log_source import (
    ConnectionTestResponse,
    LogSourceCreate,
    LogSourceResponse,
    LogSourceStatusResponse,
    LogSourceUpdate,
    ScanResultResponse,
)
from app.services import log_source_service as svc
from app.services.websocket_manager import alert_ws_manager

router = APIRouter(prefix="/api/log-sources", tags=["log-sources"])


@router.get("/", response_model=List[LogSourceResponse])
def list_sources(
    db: Session = Depends(get_db),
    _user_id: int = Depends(get_current_user_id),
):
    return svc.list_sources(db)


@router.get("/status", response_model=List[LogSourceStatusResponse])
def list_source_statuses(
    db: Session = Depends(get_db),
    _user_id: int = Depends(get_current_user_id),
):
    return svc.list_source_statuses(db)


@router.post("/", response_model=LogSourceResponse, status_code=201)
def create_source(
    data: LogSourceCreate,
    db: Session = Depends(get_db),
    _user_id: int = Depends(require_admin),
):
    return svc.create_source(db, data)


@router.get("/{source_id}", response_model=LogSourceResponse)
def get_source(
    source_id: int,
    db: Session = Depends(get_db),
    _user_id: int = Depends(get_current_user_id),
):
    return svc.get_source(db, source_id)


@router.put("/{source_id}", response_model=LogSourceResponse)
def update_source(
    source_id: int,
    data: LogSourceUpdate,
    db: Session = Depends(get_db),
    _user_id: int = Depends(require_admin),
):
    return svc.update_source(db, source_id, data)


@router.delete("/{source_id}", status_code=204)
def delete_source(
    source_id: int,
    db: Session = Depends(get_db),
    _user_id: int = Depends(require_admin),
):
    svc.delete_source(db, source_id)


@router.post("/{source_id}/test", response_model=ConnectionTestResponse)
def test_connection(
    source_id: int,
    db: Session = Depends(get_db),
    _user_id: int = Depends(require_admin),
):
    return svc.test_connection(db, source_id)


@router.post("/{source_id}/scan", response_model=ScanResultResponse)
async def scan_source(
    source_id: int,
    db: Session = Depends(get_db),
    _user_id: int = Depends(require_admin),
):
    result = svc.scan_source(db, source_id)
    alert_data = result.pop("alert_broadcast", None)
    if alert_data:
        await alert_ws_manager.broadcast({"type": "new_alert", "alert": alert_data})
    return result


@router.post("/{source_id}/re-read", response_model=ScanResultResponse)
async def re_read_source(
    source_id: int,
    db: Session = Depends(get_db),
    _user_id: int = Depends(require_admin),
):
    result = svc.re_read_source(db, source_id)
    alert_data = result.pop("alert_broadcast", None)
    if alert_data:
        await alert_ws_manager.broadcast({"type": "new_alert", "alert": alert_data})
    return result


@router.get("/{source_id}/files", response_model=List[LogFileResponse])
def list_files(
    source_id: int,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    _user_id: int = Depends(get_current_user_id),
):
    return svc.list_files(db, source_id, status)
