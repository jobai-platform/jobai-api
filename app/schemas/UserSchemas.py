import uuid
from enum import Enum

from fastapi.params import Form
from pydantic import BaseModel, EmailStr, ConfigDict, Field


class UserRoles(str, Enum):
    """Enumeration of possible user roles."""

    USER = "user"
    ADMIN = "admin"
    SUPERADMIN = "superadmin"


class UserBase(BaseModel):
    """Base schema for user information."""

    email: EmailStr
    first_name: str | None = None
    last_name: str | None = None
    username: str | None = None
    avatar: str | None = "avatars/default.png"


class UserRead(BaseModel):
    """Schema for reading user information."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: EmailStr
    username: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    role: UserRoles
    is_active: bool


class UserCreate(UserBase):
    """Schema for creating a new user."""

    password: str | None = Field(default=None, json_schema_extra={"hidden": True})
    stripe_customer_id: str | None = None

    @classmethod
    def as_form(
        cls,
        email: EmailStr = Form(),
        username: str | None = Form(default=None),
        first_name: str | None = Form(default=None),
        last_name: str | None = Form(default=None),
        password: str | None = Form(default=None),
    ) -> Self:
        return cls(
            email=email,
            username=username,
            first_name=first_name,
            last_name=last_name,
            password=password,
        )


class UserUpdate(BaseModel):
    """Schema for updating user information."""
    username: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    avatar: str | None = None
    role: UserRoles | None = None
    is_active: bool | None = None
    stripe_customer_id: str | None = None
