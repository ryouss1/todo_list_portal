from sqlalchemy import Boolean, Column, Date, DateTime, ForeignKey, Integer, String, Text, func

from app.database import Base


class CalendarEvent(Base):
    __tablename__ = "calendar_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    event_type = Column(String(20), nullable=False, default="event")
    start_at = Column(DateTime(timezone=True), nullable=False)
    end_at = Column(DateTime(timezone=True), nullable=True)
    all_day = Column(Boolean, default=False, nullable=False)
    room_id = Column(Integer, ForeignKey("calendar_rooms.id", ondelete="SET NULL"), nullable=True, index=True)
    location = Column(String(200), nullable=True)
    color = Column(String(7), nullable=True)
    visibility = Column(String(10), nullable=False, default="public")
    recurrence_rule = Column(String(500), nullable=True)
    recurrence_end = Column(Date, nullable=True)
    source_type = Column(String(20), nullable=True)
    source_id = Column(Integer, nullable=True)
    creator_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class CalendarEventException(Base):
    __tablename__ = "calendar_event_exceptions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    parent_event_id = Column(Integer, ForeignKey("calendar_events.id", ondelete="CASCADE"), nullable=False)
    original_date = Column(Date, nullable=False)
    is_deleted = Column(Boolean, default=False, nullable=False)
    override_event_id = Column(Integer, ForeignKey("calendar_events.id", ondelete="SET NULL"), nullable=True)
