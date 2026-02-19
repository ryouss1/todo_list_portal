from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.deps import get_current_user_id
from app.crud import attendance_preset as crud_preset
from app.database import get_db
from app.schemas.attendance_preset import AttendancePresetResponse

router = APIRouter(prefix="/api/attendance-presets", tags=["attendance-presets"])


@router.get("/", response_model=List[AttendancePresetResponse])
def list_presets(db: Session = Depends(get_db), _user_id: int = Depends(get_current_user_id)):
    return crud_preset.get_all_presets(db)
