from sqlalchemy import BigInteger, Boolean, Column, DateTime, Integer, String, Text, func

from app.database import Base


class LogSource(Base):
    __tablename__ = "log_sources"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(200), nullable=False)
    file_path = Column(String(1000), nullable=False)
    system_name = Column(String(200), nullable=False)
    log_type = Column(String(100), nullable=False)
    parser_pattern = Column(Text, nullable=True)
    severity_field = Column(String(100), nullable=True)
    default_severity = Column(String(20), default="INFO", nullable=False)
    polling_interval_sec = Column(Integer, default=30, nullable=False)
    is_enabled = Column(Boolean, default=True, nullable=False)
    last_read_position = Column(BigInteger, default=0, nullable=False)
    last_file_size = Column(BigInteger, default=0, nullable=False)
    last_collected_at = Column(DateTime(timezone=True), nullable=True)
    last_error = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
