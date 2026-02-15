from sqlalchemy import Boolean, Column, ForeignKey, Integer, String

from app.database import Base


class UserCalendarSetting(Base):
    __tablename__ = "user_calendar_settings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    default_color = Column(String(7), nullable=False, default="#3788d8")
    default_view = Column(String(20), nullable=False, default="dayGridMonth")
    default_reminder_minutes = Column(Integer, nullable=False, default=10)
    show_task_list = Column(Boolean, default=True, nullable=False)
    show_attendance = Column(Boolean, default=True, nullable=False)
    show_reports = Column(Boolean, default=False, nullable=False)
    working_hours_start = Column(String(5), default="09:00", nullable=False)
    working_hours_end = Column(String(5), default="18:00", nullable=False)
