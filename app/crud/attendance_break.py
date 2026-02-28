from datetime import datetime
from typing import List, Optional

from sqlalchemy.orm import Session

from app.models.attendance_break import AttendanceBreak


def get_breaks(db: Session, attendance_id: int) -> List[AttendanceBreak]:
    return (
        db.query(AttendanceBreak)
        .filter(AttendanceBreak.attendance_id == attendance_id)
        .order_by(AttendanceBreak.break_start)
        .all()
    )


def get_active_break(db: Session, attendance_id: int) -> Optional[AttendanceBreak]:
    return (
        db.query(AttendanceBreak)
        .filter(AttendanceBreak.attendance_id == attendance_id, AttendanceBreak.break_end.is_(None))
        .first()
    )


def count_breaks(db: Session, attendance_id: int) -> int:
    return db.query(AttendanceBreak).filter(AttendanceBreak.attendance_id == attendance_id).count()


def create_break(db: Session, attendance_id: int, break_start: datetime) -> AttendanceBreak:
    brk = AttendanceBreak(attendance_id=attendance_id, break_start=break_start)
    db.add(brk)
    db.commit()
    db.refresh(brk)
    return brk


def end_break(db: Session, brk: AttendanceBreak, break_end: datetime) -> AttendanceBreak:
    brk.break_end = break_end
    db.commit()
    db.refresh(brk)
    return brk


def delete_breaks_by_attendance_id(db: Session, attendance_id: int) -> None:
    """Delete all breaks for the given attendance record."""
    db.query(AttendanceBreak).filter(AttendanceBreak.attendance_id == attendance_id).delete()
    db.flush()
