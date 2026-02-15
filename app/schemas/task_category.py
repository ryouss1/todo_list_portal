from typing import Optional

from pydantic import BaseModel


class TaskCategoryCreate(BaseModel):
    name: str


class TaskCategoryUpdate(BaseModel):
    name: Optional[str] = None


class TaskCategoryResponse(BaseModel):
    id: int
    name: str

    model_config = {"from_attributes": True}
