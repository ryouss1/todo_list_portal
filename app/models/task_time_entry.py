from sqlalchemy import Column, DateTime, ForeignKey, Integer, func

from app.database import Base


class TaskTimeEntry(Base):
    __tablename__ = "task_time_entries"

    id = Column(Integer, primary_key=True, autoincrement=True)
    task_id = Column(Integer, ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False)
    started_at = Column(DateTime(timezone=True), nullable=False)
    stopped_at = Column(DateTime(timezone=True), nullable=True)
    elapsed_seconds = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
