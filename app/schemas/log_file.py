from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class LogFileResponse(BaseModel):
    id: int
    source_id: int
    path_id: int
    file_name: str
    file_size: int
    file_modified_at: Optional[datetime] = None
    last_read_line: int
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
