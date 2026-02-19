from sqlalchemy import (
    BigInteger,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    func,
)

from app.database import Base


class LogFile(Base):
    __tablename__ = "log_files"
    __table_args__ = (UniqueConstraint("path_id", "file_name", name="uq_log_files_path_file"),)

    id = Column(Integer, primary_key=True, autoincrement=True)
    source_id = Column(
        Integer,
        ForeignKey("log_sources.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    path_id = Column(
        Integer,
        ForeignKey("log_source_paths.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    file_name = Column(String(500), nullable=False)
    file_size = Column(BigInteger, nullable=False, default=0)
    file_modified_at = Column(DateTime(timezone=True), nullable=True)
    last_read_line = Column(Integer, nullable=False, default=0)  # For full_import incremental
    status = Column(String(20), nullable=False, server_default="new")  # new/unchanged/updated/deleted/error
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
