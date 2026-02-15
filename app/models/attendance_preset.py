from sqlalchemy import Column, Integer, String

from app.database import Base


class AttendancePreset(Base):
    __tablename__ = "attendance_presets"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    clock_in = Column(String(5), nullable=False)
    clock_out = Column(String(5), nullable=False)
    break_start = Column(String(5), nullable=True)
    break_end = Column(String(5), nullable=True)
