from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Index, Integer, func

from app.database import Base


class CalendarReminder(Base):
    __tablename__ = "calendar_reminders"

    id = Column(Integer, primary_key=True, autoincrement=True)
    event_id = Column(Integer, ForeignKey("calendar_events.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    minutes_before = Column(Integer, nullable=False, default=10)
    remind_at = Column(DateTime(timezone=True), nullable=False)
    is_sent = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (Index("ix_reminders_pending", "remind_at", "is_sent"),)
