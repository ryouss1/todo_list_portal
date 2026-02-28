import re
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, field_validator


class SiteGroupCreate(BaseModel):
    name: str
    description: Optional[str] = None
    color: str = "#6c757d"
    icon: Optional[str] = None
    sort_order: int = 0

    @field_validator("color")
    @classmethod
    def validate_color(cls, v: str) -> str:
        if not re.match(r"^#[0-9a-fA-F]{6}$", v):
            raise ValueError("color must be in #RRGGBB format")
        return v


class SiteGroupUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    color: Optional[str] = None
    icon: Optional[str] = None
    sort_order: Optional[int] = None

    @field_validator("color")
    @classmethod
    def validate_color(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        if not re.match(r"^#[0-9a-fA-F]{6}$", v):
            raise ValueError("color must be in #RRGGBB format")
        return v


class SiteGroupResponse(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    color: str
    icon: Optional[str] = None
    sort_order: int
    link_count: int = 0

    model_config = {"from_attributes": True}


class SiteLinkCreate(BaseModel):
    name: str
    url: str
    description: Optional[str] = None
    group_id: Optional[int] = None
    sort_order: int = 0
    is_enabled: bool = True
    check_enabled: bool = True
    check_interval_sec: int = 300
    check_timeout_sec: int = 10
    check_ssl_verify: bool = True

    @field_validator("url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        if not (v.startswith("http://") or v.startswith("https://")):
            raise ValueError("url must start with http:// or https://")
        return v

    @field_validator("check_interval_sec")
    @classmethod
    def validate_interval(cls, v: int) -> int:
        if not (60 <= v <= 3600):
            raise ValueError("check_interval_sec must be between 60 and 3600")
        return v

    @field_validator("check_timeout_sec")
    @classmethod
    def validate_timeout(cls, v: int) -> int:
        if not (3 <= v <= 60):
            raise ValueError("check_timeout_sec must be between 3 and 60")
        return v


class SiteLinkUpdate(BaseModel):
    name: Optional[str] = None
    url: Optional[str] = None
    description: Optional[str] = None
    group_id: Optional[int] = None
    sort_order: Optional[int] = None
    is_enabled: Optional[bool] = None
    check_enabled: Optional[bool] = None
    check_interval_sec: Optional[int] = None
    check_timeout_sec: Optional[int] = None
    check_ssl_verify: Optional[bool] = None

    @field_validator("url")
    @classmethod
    def validate_url(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        if not (v.startswith("http://") or v.startswith("https://")):
            raise ValueError("url must start with http:// or https://")
        return v

    @field_validator("check_interval_sec")
    @classmethod
    def validate_interval(cls, v: Optional[int]) -> Optional[int]:
        if v is None:
            return v
        if not (60 <= v <= 3600):
            raise ValueError("check_interval_sec must be between 60 and 3600")
        return v

    @field_validator("check_timeout_sec")
    @classmethod
    def validate_timeout(cls, v: Optional[int]) -> Optional[int]:
        if v is None:
            return v
        if not (3 <= v <= 60):
            raise ValueError("check_timeout_sec must be between 3 and 60")
        return v


class SiteLinkResponse(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    group_id: Optional[int] = None
    group_name: Optional[str] = None
    created_by: Optional[int] = None
    sort_order: int
    is_enabled: bool
    check_enabled: bool
    check_interval_sec: int
    check_timeout_sec: int
    check_ssl_verify: bool
    status: str
    response_time_ms: Optional[int] = None
    http_status_code: Optional[int] = None
    last_checked_at: Optional[datetime] = None
    last_status_changed_at: Optional[datetime] = None
    consecutive_failures: int
    last_error: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class SiteUrlResponse(BaseModel):
    id: int
    url: str

    model_config = {"from_attributes": True}


class SiteCheckResponse(BaseModel):
    id: int
    status: str
    previous_status: str
    response_time_ms: Optional[int] = None
    http_status_code: Optional[int] = None
    checked_at: datetime
    message: str
