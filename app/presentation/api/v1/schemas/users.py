from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field

class UserBase(BaseModel):
    email: EmailStr
    username: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    stripe_customer_id: str | None = None
    linkedin_id: str | None = None
    avatar_url: str | None = None


class UserRead(UserBase):
    id: UUID
    role: str
    is_active: bool
    created_at: datetime | None = None
    updated_at: datetime | None = None


class UserCreate(UserBase):
    password: str | None = Field(default=None, min_length=8)
    role: str = "user"
    is_active: bool = True


class UserUpdate(BaseModel):
    username: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    stripe_customer_id: str | None = None
    is_active: bool | None = None
    role: str | None = None


class UsersCountResponse(BaseModel):
    total: int
