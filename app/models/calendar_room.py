from sqlalchemy import Boolean, Column, DateTime, Integer, String, func

from app.database import Base


class CalendarRoom(Base):
    __tablename__ = "calendar_rooms"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False, unique=True)
    description = Column(String(500), nullable=True)
    capacity = Column(Integer, nullable=True)
    color = Column(String(7), nullable=True)
    sort_order = Column(Integer, nullable=False, default=0)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
