from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, func

from app.database import Base


class LogSourcePath(Base):
    __tablename__ = "log_source_paths"

    id = Column(Integer, primary_key=True, autoincrement=True)
    source_id = Column(
        Integer,
        ForeignKey("log_sources.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    base_path = Column(String(1000), nullable=False)
    file_pattern = Column(String(200), nullable=False, server_default="*.log")
    is_enabled = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
