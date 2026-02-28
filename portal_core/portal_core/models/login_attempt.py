from sqlalchemy import Boolean, Column, DateTime, Integer, String, func

from portal_core.database import Base


class LoginAttempt(Base):
    __tablename__ = "login_attempts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String(255), nullable=False, index=True)
    ip_address = Column(String(45), nullable=True)
    success = Column(Boolean, nullable=False)
    attempted_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
