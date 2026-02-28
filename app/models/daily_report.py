from sqlalchemy import Column, Date, DateTime, ForeignKey, Integer, String, Text, func

from app.database import Base


class DailyReport(Base):
    __tablename__ = "daily_reports"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    report_date = Column(Date, nullable=False)
    category_id = Column(Integer, ForeignKey("task_categories.id"), nullable=False)
    task_name = Column(String(200), nullable=False)
    backlog_ticket_id = Column(String(50), nullable=True)
    time_minutes = Column(Integer, nullable=False, default=0)
    work_content = Column(Text, nullable=False)
    achievements = Column(Text, nullable=True)
    issues = Column(Text, nullable=True)
    next_plan = Column(Text, nullable=True)
    remarks = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
