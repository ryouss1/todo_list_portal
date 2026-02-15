from sqlalchemy import Boolean, Column, DateTime, Integer, String, func

from app.database import Base


class OAuthProvider(Base):
    __tablename__ = "oauth_providers"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(50), nullable=False, unique=True)
    display_name = Column(String(100), nullable=False)
    client_id = Column(String(255), nullable=False)
    client_secret = Column(String(255), nullable=False)
    authorize_url = Column(String(500), nullable=False)
    token_url = Column(String(500), nullable=False)
    userinfo_url = Column(String(500), nullable=False)
    scopes = Column(String(500), nullable=False)
    is_enabled = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
