from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.deps import get_current_user_id
from app.database import get_db
from app.schemas.attendance import (
    AttendanceCreate,
    AttendanceResponse,
    AttendanceStatus,
    AttendanceUpdate,
    ClockInRequest,
    ClockOutRequest,
)
from app.schemas.attendance_preset import UserPresetResponse, UserPresetUpdate
from app.services import attendance_service as svc_att

router = APIRouter(prefix="/api/attendances", tags=["attendances"])


@router.post("/clock-in", response_model=AttendanceResponse, status_code=201)
def clock_in(data: ClockInRequest, db: Session = Depends(get_db), user_id: int = Depends(get_current_user_id)):
    return svc_att.clock_in(db, user_id, data.note)


@router.post("/clock-out", response_model=AttendanceResponse)
def clock_out(data: ClockOutRequest, db: Session = Depends(get_db), user_id: int = Depends(get_current_user_id)):
    return svc_att.clock_out(db, user_id, data.note)


@router.get("/status", response_model=AttendanceStatus)
def get_status(db: Session = Depends(get_db), user_id: int = Depends(get_current_user_id)):
    status = svc_att.get_status(db, user_id)
    return AttendanceStatus(
        is_clocked_in=status.is_clocked_in,
        current_attendance=status.current_attendance,
    )


@router.get("/my-preset", response_model=UserPresetResponse)
def get_my_preset(db: Session = Depends(get_db), user_id: int = Depends(get_current_user_id)):
    preset_id = svc_att.get_user_preset_id(db, user_id)
    return UserPresetResponse(default_preset_id=preset_id)


@router.put("/my-preset", response_model=UserPresetResponse)
def set_my_preset(data: UserPresetUpdate, db: Session = Depends(get_db), user_id: int = Depends(get_current_user_id)):
    svc_att.set_user_preset_id(db, user_id, data.default_preset_id)
    return UserPresetResponse(default_preset_id=data.default_preset_id)


@router.post("/default-set", response_model=AttendanceResponse)
def default_set(db: Session = Depends(get_db), user_id: int = Depends(get_current_user_id)):
    return svc_att.default_set(db, user_id)


@router.get("/export")
def export_excel(
    year: int = Query(...),
    month: int = Query(...),
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    output = svc_att.generate_monthly_excel(db, user_id, year, month)
    filename = f"attendance_{year}_{month:02d}.xlsx"
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/", response_model=List[AttendanceResponse])
def list_attendances(
    year: Optional[int] = Query(None),
    month: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    return svc_att.list_attendances(db, user_id, year=year, month=month)


@router.post("/", response_model=AttendanceResponse, status_code=201)
def create_attendance(
    data: AttendanceCreate, db: Session = Depends(get_db), user_id: int = Depends(get_current_user_id)
):
    return svc_att.create_attendance(db, user_id, data)


@router.get("/{attendance_id}", response_model=AttendanceResponse)
def get_attendance(attendance_id: int, db: Session = Depends(get_db), user_id: int = Depends(get_current_user_id)):
    return svc_att.get_attendance(db, attendance_id, user_id)


@router.put("/{attendance_id}", response_model=AttendanceResponse)
def update_attendance(
    attendance_id: int,
    data: AttendanceUpdate,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    return svc_att.update_attendance(db, attendance_id, user_id, data)


@router.delete("/{attendance_id}", status_code=204)
def delete_attendance(attendance_id: int, db: Session = Depends(get_db), user_id: int = Depends(get_current_user_id)):
    svc_att.delete_attendance(db, attendance_id, user_id)


@router.post("/{attendance_id}/break-start", response_model=AttendanceResponse)
def break_start(attendance_id: int, db: Session = Depends(get_db), user_id: int = Depends(get_current_user_id)):
    return svc_att.start_break(db, attendance_id, user_id)


@router.post("/{attendance_id}/break-end", response_model=AttendanceResponse)
def break_end(attendance_id: int, db: Session = Depends(get_db), user_id: int = Depends(get_current_user_id)):
    return svc_att.end_break(db, attendance_id, user_id)
