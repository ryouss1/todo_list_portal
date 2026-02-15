from typing import List, Optional

from sqlalchemy.orm import Session

from app.models.attendance_preset import AttendancePreset


def get_all_presets(db: Session) -> List[AttendancePreset]:
    return db.query(AttendancePreset).order_by(AttendancePreset.id).all()


def get_preset(db: Session, preset_id: int) -> Optional[AttendancePreset]:
    return db.query(AttendancePreset).filter(AttendancePreset.id == preset_id).first()
