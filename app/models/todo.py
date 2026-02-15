from sqlalchemy import Boolean, Column, Date, DateTime, ForeignKey, Integer, String, Text, func

from app.database import Base


class Todo(Base):
    __tablename__ = "todos"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    is_completed = Column(Boolean, default=False)
    priority = Column(Integer, default=0)  # 0=normal, 1=high, 2=urgent
    due_date = Column(Date, nullable=True)
    visibility = Column(String(20), nullable=False, server_default="private")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
