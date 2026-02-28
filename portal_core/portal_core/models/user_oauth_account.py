from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, UniqueConstraint, func

from portal_core.database import Base


class UserOAuthAccount(Base):
    __tablename__ = "user_oauth_accounts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    provider_id = Column(Integer, ForeignKey("oauth_providers.id", ondelete="CASCADE"), nullable=False)
    provider_user_id = Column(String(255), nullable=False)
    provider_email = Column(String(255), nullable=True)
    access_token = Column(String(2000), nullable=True)
    refresh_token = Column(String(2000), nullable=True)
    token_expires_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (UniqueConstraint("provider_id", "provider_user_id", name="uq_provider_user"),)
