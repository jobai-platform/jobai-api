import re
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.presentation.api.v1.schemas.users import UserRead

_D4_PATTERN_UPPER = re.compile(r"[A-Z]")
_D4_PATTERN_DIGIT = re.compile(r"\d")
_D4_PATTERN_SPECIAL = re.compile(r"[^A-Za-z0-9]")


def _validate_password_policy(value: str) -> str:
    if len(value) < 12:
        raise ValueError("Password must be at least 12 characters")
    if not _D4_PATTERN_UPPER.search(value):
        raise ValueError("Password must contain at least one uppercase letter")
    if not _D4_PATTERN_DIGIT.search(value):
        raise ValueError("Password must contain at least one digit")
    if not _D4_PATTERN_SPECIAL.search(value):
        raise ValueError("Password must contain at least one special character")
    return value


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    first_name: str = Field(min_length=1)
    last_name: str = Field(min_length=1)

    @field_validator("password")
    @classmethod
    def validate_d4(cls, v: str) -> str:
        return _validate_password_policy(v)


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str = Field(min_length=1)
    new_password: str

    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, value: str) -> str:
        return _validate_password_policy(value)


class RegisterResponse(BaseModel):
    user: UserRead
    access_token: str
    token_type: str = "Bearer"


class TokenPairSchema(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "Bearer"


class AccessTokenResponse(BaseModel):
    access_token: str
    token_type: str = "Bearer"


class TokenPayload(BaseModel):
    sub: UUID


class RefreshToken(BaseModel):
    refresh_token: str


class LinkedInCallbackRequest(BaseModel):
    code: str
    redirect_uri: str
    state: str = Field(min_length=1)


class LinkedInAuthUrlResponse(BaseModel):
    authorization_url: str
    state: str  # frontend stores this in sessionStorage for CSRF verification


class LinkedInCallbackResponse(BaseModel):
    access_token: str
    is_new_user: bool
    token_type: str = "Bearer"


class LinkedInCodeResponse(BaseModel):
    code: str
    redirect_uri: str
