from typing import List

from fastapi import APIRouter, BackgroundTasks, Depends
from sqlalchemy.orm import Session

from app.core.deps import get_current_user_id
from app.database import get_db
from app.schemas.presence import (
    PresenceLogResponse,
    PresenceStatusResponse,
    PresenceStatusWithUser,
    PresenceUpdateRequest,
)
from app.services import presence_service as svc_presence
from app.services.websocket_manager import presence_ws_manager

router = APIRouter(prefix="/api/presence", tags=["presence"])


@router.put("/status", response_model=PresenceStatusResponse)
async def update_status(
    data: PresenceUpdateRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    result = svc_presence.update_status(db, user_id, data.status, data.message)
    await presence_ws_manager.broadcast(
        {"type": "presence_update", "user_id": user_id, "status": data.status, "message": data.message}
    )
    return result


@router.get("/statuses", response_model=List[PresenceStatusWithUser])
def list_statuses(db: Session = Depends(get_db), _user_id: int = Depends(get_current_user_id)):
    return svc_presence.get_all_statuses(db)


@router.get("/me", response_model=PresenceStatusResponse)
def get_my_status(db: Session = Depends(get_db), user_id: int = Depends(get_current_user_id)):
    return svc_presence.get_my_status(db, user_id)


@router.get("/logs", response_model=List[PresenceLogResponse])
def get_logs(db: Session = Depends(get_db), user_id: int = Depends(get_current_user_id)):
    return svc_presence.get_logs(db, user_id)
