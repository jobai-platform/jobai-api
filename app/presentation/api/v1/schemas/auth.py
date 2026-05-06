from uuid import UUID

from pydantic import BaseModel, HttpUrl


class TokenPairSchema(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "Bearer"


class TokenPayload(BaseModel):
    sub: UUID


class RefreshToken(BaseModel):
    refresh_token: str


class LinkedInCallbackRequest(BaseModel):
    code: str
    redirect_uri: str


class LinkedInAuthUrlResponse(BaseModel):
    authorization_url: str
