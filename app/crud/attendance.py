from datetime import date, datetime, timezone
from typing import List, Optional

from sqlalchemy.orm import Session

from app.crud.base import CRUDBase
from app.models.attendance import Attendance

_crud = CRUDBase(Attendance)

get_attendance = _crud.get


def get_current_attendance(db: Session, user_id: int) -> Optional[Attendance]:
    return db.query(Attendance).filter(Attendance.user_id == user_id, Attendance.clock_out.is_(None)).first()


def clock_in(db: Session, user_id: int, note: Optional[str] = None) -> Attendance:
    now = datetime.now(timezone.utc)
    attendance = Attendance(
        user_id=user_id,
        clock_in=now,
        date=now.date(),
        note=note,
    )
    db.add(attendance)
    db.commit()
    db.refresh(attendance)
    return attendance


def clock_out(db: Session, attendance: Attendance, note: Optional[str] = None) -> Attendance:
    attendance.clock_out = datetime.now(timezone.utc)
    if note is not None:
        attendance.note = note
    db.commit()
    db.refresh(attendance)
    return attendance


def get_attendances(
    db: Session, user_id: int, year: Optional[int] = None, month: Optional[int] = None
) -> List[Attendance]:
    q = db.query(Attendance).filter(Attendance.user_id == user_id)
    if year is not None and month is not None:
        start = date(year, month, 1)
        end = date(year + 1, 1, 1) if month == 12 else date(year, month + 1, 1)
        q = q.filter(Attendance.date >= start, Attendance.date < end)
    return q.order_by(Attendance.date.desc(), Attendance.clock_in.desc()).all()


def get_attendance_by_date(db: Session, user_id: int, target_date: date) -> Optional[Attendance]:
    return db.query(Attendance).filter(Attendance.user_id == user_id, Attendance.date == target_date).first()


def create_attendance(
    db: Session,
    user_id: int,
    target_date: date,
    clock_in: datetime,
    clock_out: Optional[datetime] = None,
    note: Optional[str] = None,
) -> Attendance:
    attendance = Attendance(
        user_id=user_id,
        date=target_date,
        clock_in=clock_in,
        clock_out=clock_out,
        note=note,
    )
    db.add(attendance)
    db.commit()
    db.refresh(attendance)
    return attendance


def update_attendance(db: Session, attendance: Attendance, data: dict) -> Attendance:
    return _crud.update(db, attendance, data)


delete_attendance = _crud.delete
