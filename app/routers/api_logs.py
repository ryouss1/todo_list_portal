from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.config import API_LOG_LIMIT
from app.core.deps import get_current_user_id
from app.database import get_db
from app.schemas.log import LogCreate, LogResponse
from app.services import log_service as svc_log

router = APIRouter(prefix="/api/logs", tags=["logs"])


@router.post("/", response_model=LogResponse, status_code=201)
async def create_log(data: LogCreate, db: Session = Depends(get_db)):
    """Create a log entry. Public endpoint for external log ingestion."""
    return await svc_log.create_log(db, data)


@router.get("/", response_model=List[LogResponse])
def list_logs(
    limit: int = API_LOG_LIMIT,
    db: Session = Depends(get_db),
    _user_id: int = Depends(get_current_user_id),
):
    return svc_log.list_logs(db, limit)


@router.get("/important", response_model=List[LogResponse])
def list_important_logs(
    limit: int = API_LOG_LIMIT,
    db: Session = Depends(get_db),
    _user_id: int = Depends(get_current_user_id),
):
    return svc_log.list_important_logs(db, limit)
