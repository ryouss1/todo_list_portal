import os
import re
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, field_validator

from app.config import LOG_ALLOWED_PATHS, LOG_SOURCE_DEFAULT_POLLING_SEC, LOG_SOURCE_MIN_POLLING_SEC


def _validate_file_path(v: str) -> str:
    """Validate file_path: must be absolute, no traversal, within allowed dirs."""
    if not os.path.isabs(v):
        raise ValueError("file_path must be an absolute path")
    # Resolve to canonical path to catch .. traversal
    resolved = os.path.realpath(v)
    if ".." in v.split(os.sep):
        raise ValueError("file_path must not contain '..'")
    # Check allowed directories
    allowed = LOG_ALLOWED_PATHS.strip()
    if allowed:
        allowed_dirs = [d.strip() for d in allowed.split(",") if d.strip()]
        if not any(resolved.startswith(os.path.realpath(d)) for d in allowed_dirs):
            raise ValueError(f"file_path must be under one of: {', '.join(allowed_dirs)}")
    return v


class LogSourceCreate(BaseModel):
    name: str
    file_path: str
    system_name: str
    log_type: str
    parser_pattern: Optional[str] = None
    severity_field: Optional[str] = None
    default_severity: str = "INFO"
    polling_interval_sec: int = LOG_SOURCE_DEFAULT_POLLING_SEC
    is_enabled: bool = True

    @field_validator("file_path")
    @classmethod
    def validate_file_path(cls, v: str) -> str:
        return _validate_file_path(v)

    @field_validator("parser_pattern")
    @classmethod
    def validate_regex(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            try:
                re.compile(v)
            except re.error as e:
                raise ValueError(f"Invalid regex pattern: {e}")
        return v

    @field_validator("polling_interval_sec")
    @classmethod
    def validate_interval(cls, v: int) -> int:
        if v < LOG_SOURCE_MIN_POLLING_SEC:
            raise ValueError(f"polling_interval_sec must be at least {LOG_SOURCE_MIN_POLLING_SEC}")
        return v


class LogSourceUpdate(BaseModel):
    name: Optional[str] = None
    file_path: Optional[str] = None
    system_name: Optional[str] = None
    log_type: Optional[str] = None
    parser_pattern: Optional[str] = None
    severity_field: Optional[str] = None
    default_severity: Optional[str] = None
    polling_interval_sec: Optional[int] = None
    is_enabled: Optional[bool] = None

    @field_validator("file_path")
    @classmethod
    def validate_file_path(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            return _validate_file_path(v)
        return v

    @field_validator("parser_pattern")
    @classmethod
    def validate_regex(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            try:
                re.compile(v)
            except re.error as e:
                raise ValueError(f"Invalid regex pattern: {e}")
        return v

    @field_validator("polling_interval_sec")
    @classmethod
    def validate_interval(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and v < 5:
            raise ValueError("polling_interval_sec must be at least 5")
        return v


class LogSourceResponse(BaseModel):
    id: int
    name: str
    file_path: str
    system_name: str
    log_type: str
    parser_pattern: Optional[str] = None
    severity_field: Optional[str] = None
    default_severity: str
    polling_interval_sec: int
    is_enabled: bool
    last_read_position: int
    last_file_size: int
    last_collected_at: Optional[datetime] = None
    last_error: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class LogSourceStatusResponse(BaseModel):
    id: int
    name: str
    is_enabled: bool
    last_collected_at: Optional[datetime] = None
    last_error: Optional[str] = None

    model_config = {"from_attributes": True}
