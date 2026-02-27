from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text, func

from app.database import Base


class LogSource(Base):
    __tablename__ = "log_sources"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(200), nullable=False)  # Display name
    department_id = Column(Integer, ForeignKey("departments.id"), nullable=False)
    access_method = Column(String(10), nullable=False)  # "ftp" or "smb"
    host = Column(String(255), nullable=False)  # Host/IP
    port = Column(Integer, nullable=True)  # NULL = default (FTP=21, SMB=445)
    username = Column(String(500), nullable=False)  # Encrypted
    password = Column(String(500), nullable=False)  # Encrypted
    domain = Column(String(200), nullable=True)  # SMB domain (optional)
    encoding = Column(String(20), nullable=False, server_default="utf-8")  # File encoding
    source_type = Column(String(20), nullable=False, server_default="OTHER")  # WEB/HT/BATCH/OTHER
    polling_interval_sec = Column(Integer, nullable=False, default=60)  # 60-300
    collection_mode = Column(String(20), nullable=False, server_default="metadata_only")  # metadata_only/full_import
    parser_pattern = Column(Text, nullable=True)  # Regex (full_import only)
    severity_field = Column(String(100), nullable=True)  # Severity group name
    default_severity = Column(String(20), nullable=False, server_default="INFO")
    is_enabled = Column(Boolean, nullable=False, default=True)
    alert_on_change = Column(Boolean, nullable=False, server_default="false")
    consecutive_errors = Column(Integer, nullable=False, default=0)  # For auto-disable
    last_checked_at = Column(DateTime(timezone=True), nullable=True)
    last_error = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
