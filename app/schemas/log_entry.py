from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel


class LogEntryResponse(BaseModel):
    id: int
    file_id: int
    line_number: int
    severity: str
    message: str
    received_at: datetime

    model_config = {"from_attributes": True}


class LogEntryContentResponse(BaseModel):
    """Response for file content viewing (full_import mode)."""

    file_name: str
    total_lines: int
    lines: List[LogEntryResponse]
    has_more: bool = False
    next_cursor: Optional[str] = None  # Cursor for pagination


class LogEntrySearchResponse(BaseModel):
    """Response for log search API."""

    entries: List[LogEntryResponse]
    total_count: int
    has_more: bool = False
    next_cursor: Optional[str] = None
