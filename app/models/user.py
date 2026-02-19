from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, func

from app.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String(255), nullable=False, unique=True)
    display_name = Column(String(200), nullable=False)
    password_hash = Column(String(255), nullable=True)
    role = Column(String(20), nullable=False, server_default="user")
    is_active = Column(Boolean, default=True)
    default_preset_id = Column(Integer, ForeignKey("attendance_presets.id"), nullable=True)
    group_id = Column(Integer, ForeignKey("groups.id", ondelete="SET NULL"), nullable=True, index=True)
    locked_until = Column(DateTime(timezone=True), nullable=True)
    session_version = Column(Integer, nullable=False, server_default="1")
    preferred_locale = Column(String(10), nullable=False, server_default="ja")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
