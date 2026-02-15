from sqlalchemy import Column, Date, DateTime, ForeignKey, Integer, String, Text, func

from app.database import Base


class TaskListItem(Base):
    __tablename__ = "task_list_items"

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    scheduled_date = Column(Date, nullable=True)
    assignee_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    status = Column(String(20), default="open", nullable=False)
    total_seconds = Column(Integer, default=0, nullable=False)
    category_id = Column(Integer, ForeignKey("task_categories.id"), nullable=True)
    backlog_ticket_id = Column(String(50), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
