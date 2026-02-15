from typing import Optional

from pydantic import BaseModel


class AttendancePresetResponse(BaseModel):
    id: int
    name: str
    clock_in: str
    clock_out: str
    break_start: Optional[str] = None
    break_end: Optional[str] = None

    model_config = {"from_attributes": True}


class UserPresetResponse(BaseModel):
    default_preset_id: Optional[int] = None


class UserPresetUpdate(BaseModel):
    default_preset_id: int
