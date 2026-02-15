from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel


class LogCreate(BaseModel):
    system_name: str
    log_type: str
    severity: str = "INFO"
    message: str
    extra_data: Optional[Any] = None


class LogResponse(BaseModel):
    id: int
    system_name: str
    log_type: str
    severity: str
    message: str
    extra_data: Optional[Any] = None
    received_at: datetime

    model_config = {"from_attributes": True}
