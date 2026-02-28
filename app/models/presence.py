from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, func

from app.database import Base


class PresenceStatus(Base):
    __tablename__ = "presence_statuses"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, unique=True)
    status = Column(String(20), nullable=False, server_default="offline")
    message = Column(Text, nullable=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class PresenceLog(Base):
    __tablename__ = "presence_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    status = Column(String(20), nullable=False)
    message = Column(Text, nullable=True)
    changed_at = Column(DateTime(timezone=True), server_default=func.now())
