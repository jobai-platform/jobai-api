from uuid import UUID

from pydantic import BaseModel


class Token(BaseModel):
    """ Schema class representing a JWT auth token. """
    access_token: str
    token_type: str
    token_type: str = "Bearer"


class TokenPayload(BaseModel):
    sub: UUID


class RefreshTokenPayload(BaseModel):
    refresh_token: str


class GoogleTokenPayload(BaseModel):
    """ Schema class representing a Google OAuth2 token payload. """
    google_oauth2_token: str
