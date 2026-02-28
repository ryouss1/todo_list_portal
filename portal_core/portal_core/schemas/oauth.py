"""OAuth Pydantic schemas."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class OAuthProviderPublic(BaseModel):
    """Public provider info (for login page)."""

    name: str
    display_name: str

    model_config = {"from_attributes": True}


class OAuthProviderResponse(BaseModel):
    """Full provider info (admin)."""

    id: int
    name: str
    display_name: str
    client_id: str
    authorize_url: str
    token_url: str
    userinfo_url: str
    scopes: str
    is_enabled: bool
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class OAuthProviderCreate(BaseModel):
    name: str
    display_name: str
    client_id: str
    client_secret: str
    authorize_url: str
    token_url: str
    userinfo_url: str
    scopes: str
    is_enabled: bool = True


class OAuthProviderUpdate(BaseModel):
    display_name: Optional[str] = None
    client_id: Optional[str] = None
    client_secret: Optional[str] = None
    authorize_url: Optional[str] = None
    token_url: Optional[str] = None
    userinfo_url: Optional[str] = None
    scopes: Optional[str] = None
    is_enabled: Optional[bool] = None


class OAuthLinkResponse(BaseModel):
    """User's linked OAuth account info."""

    id: int
    provider_name: str
    provider_display_name: str
    provider_email: Optional[str] = None
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}
