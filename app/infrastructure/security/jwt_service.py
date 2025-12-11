import uuid
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from typing import Optional, Mapping

from jose import jwt

from app.application.auth.ports import TokenService
from app.core.config import settings


@dataclass(frozen=True)
class JWTSettings:
    secret: str
    algorithm: str = 'HS256',
    access_token_expire_minutes: int = 60
    refresh_token_expire_days: int = 7
    issuer: str = "jobai-backend"
    audience: str = 'jobai-frontend'


class JWTService:

    def __init__(self, cfg: Optional[JWTSettings] = None) -> None:
        self.cfg = cfg or JWTSettings(
            secret=getattr(settings, "JWT_SECRET_KEY", settings.SECRET_KEY),
            algorithm=getattr(settings, "JWT_ALGORITHM",getattr(settings, "JWT_ALGORITHM", "HS256")),
            access_token_expire_minutes=getattr(settings, "JWT_ACCESS_TOKEN_EXPIRE_MINUTES", 60),
            refresh_token_expire_days=getattr(settings, "JWT_REFRESH_TOKEN_EXPIRE_DAYS", 7),
            issuer=getattr(settings, "JWT_ISSUER", "jobai-backend"),
            audience=getattr(settings, "JWT_AUDIENCE", "jobai-frontend"),
        )

    def _now(self) -> datetime:
        return datetime.now(timezone.utc)

    def _base_claims(self, subject: str) -> dict[str, any]:
        now = self._now()
        return {
            "sub": subject,
            "iss": self.cfg.issuer,
            "aud": self.cfg.audience,
            "iat": now,
            "nbf": now,
            "jti": str(uuid.uuid4()),
        }

    def _encode(self, claims: Mapping[str, any]) -> str:
        return jwt.encode(claims, self.cfg.secret, algorithm=self.cfg.algorithm)

    def _decode(self, token: str) -> Mapping[str, any]:
        return jwt.decode(
            token,
            self.cfg.secret,
            algorithms=[self.cfg.algorithm],
            issuer=self.cfg.issuer,
            audience=self.cfg.audience,
            options={
                "require": True,
                "require_iat": True,
                "require_nbf": True,
            }
        )

    def create_access_token(self, subject: str, extra: Optional[Mapping[str, any]] = None) -> str:
        payload = self._base_claims(subject)
        if extra:
            payload.update(extra)
        payload["type"] = "access"
        payload["exp"] = self._now() + timedelta(minutes=self.cfg.access_token_expire_minutes)
        return self._encode(payload)

    def create_refresh_token(self, subject: str, extra: Optional[Mapping[str, any]] = None) -> str:
        payload = self._base_claims(subject)
        if extra:
            payload.update(extra)
        payload["type"] = "refresh"
        payload["exp"] = self._now() + timedelta(minutes=self.cfg.refresh_token_expire_days)
        return self._encode(payload)

    def decode_token(self, token: str) -> Mapping[str, any]:
        return self._decode(token)


class JWTTokenServiceAdapter(TokenService):
    """
    Adapter between JWTService (Infra) and the port TokenService (Application)
    """

    def __init__(self, service: Optional[JWTService] = None) -> None:
        self._service = service or JWTService()

    def create_access_token(
        self,
        subject: str,
        extra: Optional[Mapping[str, any]] = None,
    ) -> str:
        return self._service.create_access_token(subject, extra)

    def create_refresh_token(
        self,
        subject: str,
        extra: Optional[Mapping[str, any]] = None,
    ) -> str:
        return self._service.create_refresh_token(subject, extra)

    def decode_token(self, token: str) -> Mapping[str, any]:
        return self._service.decode_token(token)
