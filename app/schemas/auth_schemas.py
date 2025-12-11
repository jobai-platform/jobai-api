from uuid import UUID

from pydantic import BaseModel


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "Bearer"


class TokenPayload(BaseModel):
    sub: UUID


class RefreshToken(BaseModel):
    refresh_token: str
