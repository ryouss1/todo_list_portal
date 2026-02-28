from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import relationship

from app.database import Base


class SiteGroup(Base):
    __tablename__ = "site_groups"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False, unique=True)
    description = Column(String(500), nullable=True)
    color = Column(String(7), nullable=False, server_default="#6c757d")
    icon = Column(String(50), nullable=True)
    sort_order = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class SiteLink(Base):
    __tablename__ = "site_links"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(200), nullable=False)
    url = Column(String(2000), nullable=False)
    description = Column(String(500), nullable=True)
    group_id = Column(Integer, ForeignKey("site_groups.id", ondelete="SET NULL"), nullable=True, index=True)
    created_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    sort_order = Column(Integer, nullable=False, default=0)
    is_enabled = Column(Boolean, nullable=False, default=True)
    check_enabled = Column(Boolean, nullable=False, default=True)
    check_interval_sec = Column(Integer, nullable=False, default=300)
    check_timeout_sec = Column(Integer, nullable=False, default=10)
    check_ssl_verify = Column(Boolean, nullable=False, default=True)
    status = Column(String(20), nullable=False, server_default="unknown")
    response_time_ms = Column(Integer, nullable=True)
    http_status_code = Column(Integer, nullable=True)
    last_checked_at = Column(DateTime(timezone=True), nullable=True)
    last_status_changed_at = Column(DateTime(timezone=True), nullable=True)
    consecutive_failures = Column(Integer, nullable=False, default=0)
    last_error = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    group = relationship("SiteGroup", foreign_keys=[group_id], lazy="joined")
