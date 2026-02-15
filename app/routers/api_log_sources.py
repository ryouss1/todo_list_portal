from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.deps import get_current_user_id, require_admin
from app.database import get_db
from app.schemas.log_source import LogSourceCreate, LogSourceResponse, LogSourceStatusResponse, LogSourceUpdate
from app.services import log_source_service as svc

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
    return svc.list_sources(db)


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
