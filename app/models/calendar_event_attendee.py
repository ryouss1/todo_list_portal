from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, UniqueConstraint, func

from app.database import Base


class CalendarEventAttendee(Base):
    __tablename__ = "calendar_event_attendees"

    id = Column(Integer, primary_key=True, autoincrement=True)
    event_id = Column(Integer, ForeignKey("calendar_events.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    response_status = Column(String(10), nullable=False, default="pending")
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (UniqueConstraint("event_id", "user_id", name="uq_event_attendee"),)
