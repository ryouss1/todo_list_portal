import re
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, field_validator

from app.config import LOG_SOURCE_MAX_POLLING_SEC, LOG_SOURCE_MIN_POLLING_SEC, LOG_SOURCE_TYPES


class LogSourcePathCreate(BaseModel):
    base_path: str
    file_pattern: str = "*.log"
    is_enabled: bool = True


class LogSourcePathUpdate(BaseModel):
    id: Optional[int] = None  # None = new path, int = existing path to update
    base_path: str
    file_pattern: str = "*.log"
    is_enabled: bool = True


class LogSourcePathResponse(BaseModel):
    id: int
    source_id: int
    base_path: str
    file_pattern: str
    is_enabled: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class LogSourceCreate(BaseModel):
    name: str
    group_id: int
    access_method: str  # "ftp" or "smb"
    host: str
    port: Optional[int] = None
    username: str
    password: str
    domain: Optional[str] = None
    paths: List[LogSourcePathCreate]
    encoding: str = "utf-8"
    source_type: str = "OTHER"
    polling_interval_sec: int = 60
    collection_mode: str = "metadata_only"  # metadata_only or full_import
    parser_pattern: Optional[str] = None
    severity_field: Optional[str] = None
    default_severity: str = "INFO"
    is_enabled: bool = True
    alert_on_change: bool = False

    @field_validator("access_method")
    @classmethod
    def validate_access_method(cls, v: str) -> str:
        if v not in ("ftp", "smb"):
            raise ValueError("access_method must be 'ftp' or 'smb'")
        return v

    @field_validator("collection_mode")
    @classmethod
    def validate_collection_mode(cls, v: str) -> str:
        if v not in ("metadata_only", "full_import"):
            raise ValueError("collection_mode must be 'metadata_only' or 'full_import'")
        return v

    @field_validator("source_type")
    @classmethod
    def validate_source_type(cls, v: str) -> str:
        if v not in LOG_SOURCE_TYPES:
            raise ValueError(f"source_type must be one of: {', '.join(LOG_SOURCE_TYPES)}")
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
    def validate_interval(cls, v: int) -> int:
        if v < LOG_SOURCE_MIN_POLLING_SEC:
            raise ValueError(f"polling_interval_sec must be at least {LOG_SOURCE_MIN_POLLING_SEC}")
        if v > LOG_SOURCE_MAX_POLLING_SEC:
            raise ValueError(f"polling_interval_sec must be at most {LOG_SOURCE_MAX_POLLING_SEC}")
        return v

    @field_validator("paths")
    @classmethod
    def validate_paths_not_empty(cls, v: List[LogSourcePathCreate]) -> List[LogSourcePathCreate]:
        if not v:
            raise ValueError("At least one path is required")
        return v


class LogSourceUpdate(BaseModel):
    name: Optional[str] = None
    group_id: Optional[int] = None
    access_method: Optional[str] = None
    host: Optional[str] = None
    port: Optional[int] = None
    username: Optional[str] = None
    password: Optional[str] = None
    domain: Optional[str] = None
    paths: Optional[List[LogSourcePathUpdate]] = None
    encoding: Optional[str] = None
    source_type: Optional[str] = None
    polling_interval_sec: Optional[int] = None
    collection_mode: Optional[str] = None
    parser_pattern: Optional[str] = None
    severity_field: Optional[str] = None
    default_severity: Optional[str] = None
    is_enabled: Optional[bool] = None
    alert_on_change: Optional[bool] = None

    @field_validator("access_method")
    @classmethod
    def validate_access_method(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in ("ftp", "smb"):
            raise ValueError("access_method must be 'ftp' or 'smb'")
        return v

    @field_validator("collection_mode")
    @classmethod
    def validate_collection_mode(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in ("metadata_only", "full_import"):
            raise ValueError("collection_mode must be 'metadata_only' or 'full_import'")
        return v

    @field_validator("source_type")
    @classmethod
    def validate_source_type(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in LOG_SOURCE_TYPES:
            raise ValueError(f"source_type must be one of: {', '.join(LOG_SOURCE_TYPES)}")
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
        if v is not None:
            if v < LOG_SOURCE_MIN_POLLING_SEC:
                raise ValueError(f"polling_interval_sec must be at least {LOG_SOURCE_MIN_POLLING_SEC}")
            if v > LOG_SOURCE_MAX_POLLING_SEC:
                raise ValueError(f"polling_interval_sec must be at most {LOG_SOURCE_MAX_POLLING_SEC}")
        return v

    @field_validator("paths")
    @classmethod
    def validate_paths_not_empty(cls, v: Optional[List[LogSourcePathUpdate]]) -> Optional[List[LogSourcePathUpdate]]:
        if v is not None and len(v) == 0:
            raise ValueError("At least one path is required")
        return v


class LogSourceResponse(BaseModel):
    id: int
    name: str
    group_id: int
    group_name: str
    access_method: str
    host: str
    port: Optional[int] = None
    username_masked: str  # Masked username for display
    domain: Optional[str] = None
    paths: List[LogSourcePathResponse]
    encoding: str
    source_type: str
    polling_interval_sec: int
    collection_mode: str
    parser_pattern: Optional[str] = None
    severity_field: Optional[str] = None
    default_severity: str
    is_enabled: bool
    alert_on_change: bool
    consecutive_errors: int
    last_checked_at: Optional[datetime] = None
    last_error: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ChangedPathInfo(BaseModel):
    """Per-path details of changed files with folder link."""

    path_id: int
    base_path: str
    folder_link: str
    copy_path: str = ""
    new_files: List[str] = []
    updated_files: List[str] = []


class LogSourceStatusResponse(BaseModel):
    """Status for source dashboard table with changed file details."""

    id: int
    name: str
    group_id: int
    group_name: str
    access_method: str
    host: str
    source_type: str
    collection_mode: str
    is_enabled: bool
    alert_on_change: bool = False
    consecutive_errors: int
    last_checked_at: Optional[datetime] = None
    last_error: Optional[str] = None
    path_count: int = 0
    file_count: int = 0
    new_file_count: int = 0
    updated_file_count: int = 0
    has_alert: bool = False
    changed_paths: List[ChangedPathInfo] = []


class PathTestResult(BaseModel):
    base_path: str
    file_pattern: str
    status: str  # "ok" or "error"
    file_count: int = 0
    message: str


class ConnectionTestResponse(BaseModel):
    status: str  # "ok" or "error"
    file_count: int = 0
    message: str
    path_results: List[PathTestResult] = []


class ScanResultResponse(BaseModel):
    file_count: int = 0
    new_count: int = 0
    updated_count: int = 0
    alerts_created: int = 0
    message: str
    changed_paths: List[ChangedPathInfo] = []
    content_read_files: int = 0
