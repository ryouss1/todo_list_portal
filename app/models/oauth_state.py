from sqlalchemy import Column, DateTime, Integer, String, func

from app.database import Base


class OAuthState(Base):
    __tablename__ = "oauth_states"

    id = Column(Integer, primary_key=True, autoincrement=True)
    state = Column(String(128), nullable=False, unique=True)
    code_verifier = Column(String(128), nullable=True)
    redirect_uri = Column(String(500), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=False)
