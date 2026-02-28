from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel

from app.constants import PresenceStatusType

PRESENCE_STATUSES = PresenceStatusType


class PresenceUpdateRequest(BaseModel):
    status: PRESENCE_STATUSES
    message: Optional[str] = None


class PresenceStatusResponse(BaseModel):
    id: int
    user_id: int
    status: str
    message: Optional[str] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class ActiveTicket(BaseModel):
    task_id: int
    task_title: str
    backlog_ticket_id: str


class PresenceStatusWithUser(BaseModel):
    user_id: int
    display_name: str
    status: str
    message: Optional[str] = None
    updated_at: Optional[datetime] = None
    active_tickets: List[ActiveTicket] = []


class PresenceLogResponse(BaseModel):
    id: int
    user_id: int
    status: str
    message: Optional[str] = None
    changed_at: Optional[datetime] = None

    model_config = {"from_attributes": True}
