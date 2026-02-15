from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text, func

from app.database import Base


class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(String(20), default="pending")
    total_seconds = Column(Integer, default=0)
    report = Column(Boolean, default=False)
    category_id = Column(Integer, ForeignKey("task_categories.id"), nullable=True)
    backlog_ticket_id = Column(String(50), nullable=True)
    source_item_id = Column(Integer, ForeignKey("task_list_items.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
