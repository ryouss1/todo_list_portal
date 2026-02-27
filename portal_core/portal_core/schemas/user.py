from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, EmailStr

from portal_core.core.constants import UserRoleType


class UserCreate(BaseModel):
    email: EmailStr
    display_name: str
    password: str
    role: UserRoleType = "user"


class UserResponse(BaseModel):
    id: int
    email: str
    display_name: str
    role: str
    is_active: bool
    department_id: Optional[int] = None
    department_name: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class UserUpdate(BaseModel):
    display_name: Optional[str] = None
    email: Optional[EmailStr] = None
    role: Optional[UserRoleType] = None
    is_active: Optional[bool] = None
    department_id: Optional[int] = None
    preferred_locale: Optional[Literal["ja", "en"]] = None


class PasswordChange(BaseModel):
    current_password: str
    new_password: str


class PasswordReset(BaseModel):
    new_password: str
