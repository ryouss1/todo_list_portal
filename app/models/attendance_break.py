from sqlalchemy import Column, DateTime, ForeignKey, Integer, func

from app.database import Base


class AttendanceBreak(Base):
    __tablename__ = "attendance_breaks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    attendance_id = Column(Integer, ForeignKey("attendances.id", ondelete="CASCADE"), nullable=False)
    break_start = Column(DateTime(timezone=True), nullable=False)
    break_end = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
