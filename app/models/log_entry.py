from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, String, Text, func

from app.database import Base


class LogEntry(Base):
    __tablename__ = "log_entries"
    __table_args__ = (
        Index("ix_log_entries_file_line", "file_id", "line_number"),
        Index("ix_log_entries_received_at", "received_at"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    file_id = Column(
        Integer,
        ForeignKey("log_files.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    line_number = Column(Integer, nullable=False)
    severity = Column(String(20), nullable=False, server_default="INFO")
    message = Column(Text, nullable=False)
    received_at = Column(DateTime(timezone=True), server_default=func.now())
