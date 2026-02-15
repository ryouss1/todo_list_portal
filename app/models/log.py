from sqlalchemy import JSON, Column, DateTime, Integer, String, Text, func

from app.database import Base


class Log(Base):
    __tablename__ = "logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    system_name = Column(String(200), nullable=False)
    log_type = Column(String(100), nullable=False)
    severity = Column(String(20), default="INFO")
    message = Column(Text, nullable=False)
    extra_data = Column(JSON, nullable=True)
    received_at = Column(DateTime(timezone=True), server_default=func.now())
