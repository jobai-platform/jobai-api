from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
import uuid

from jose import jwt

from app.application.auth.ports import TokenService
from app.core.config import settings
from app.domain.common.exceptions import UnauthorizedError


@dataclass(frozen=True)
class JWTSettings:
    secret: str
    algorithm: str = 'HS256',
    access_token_expire_minutes: int = 60
    refresh_token_expire_days: int = 7
    issuer: str = "jobai-backend"
    audience: str = 'jobai-frontend'


class JWTService:

    def __init__(self, cfg: JWTSettings | None = None) -> None:
        self.cfg = cfg or JWTSettings(
            secret=getattr(settings, "JWT_SECRET_KEY", settings.SECRET_KEY),
            algorithm=getattr(settings, "JWT_ALGORITHM", "HS256"),
            access_token_expire_minutes=getattr(settings, "JWT_ACCESS_TOKEN_EXPIRE_MINUTES", 60),
            refresh_token_expire_days=getattr(settings, "JWT_REFRESH_TOKEN_EXPIRE_DAYS", 7),
            issuer=getattr(settings, "JWT_ISSUER", "jobai-backend"),
            audience=getattr(settings, "JWT_AUDIENCE", "jobai-frontend"),
        )

    def _now(self) -> datetime:
        return datetime.now(UTC)

    def _base_claims(self, subject: str) -> dict[str, object]:
        now = self._now()
        return {
            "sub": subject,
            "iss": self.cfg.issuer,
            "aud": self.cfg.audience,
            "iat": now,
            "nbf": now,
            "jti": str(uuid.uuid4()),
        }

    def _encode(self, claims: Mapping[str, object]) -> str:
        return jwt.encode(claims, self.cfg.secret, algorithm=self.cfg.algorithm)

    def _decode(self, token: str) -> Mapping[str, object]:
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

    def create_access_token(self, subject: str, extra: Mapping[str, object] | None = None) -> str:
        payload = self._base_claims(subject)
        if extra:
            payload.update(extra)
        payload["type"] = "access"
        payload["exp"] = self._now() + timedelta(minutes=self.cfg.access_token_expire_minutes)
        return self._encode(payload)

    def create_refresh_token(self, subject: str, extra: Mapping[str, object] | None = None) -> str:
        payload = self._base_claims(subject)
        if extra:
            payload.update(extra)
        payload["type"] = "refresh"
        payload["exp"] = self._now() + timedelta(days=self.cfg.refresh_token_expire_days)
        return self._encode(payload)

    def decode_token(self, token: str) -> Mapping[str, object]:
        return self._decode(token)

    def validate_refresh_token(self, token: str) -> str:
        try:
            claims = self._decode(token)
        except Exception as exc:
            raise UnauthorizedError(
                code="invalid_token", details="Invalid or expired token"
            ) from exc
        if claims.get("type") != "refresh":
            raise UnauthorizedError(code="invalid_token", details="Token is not a refresh token")
        return str(claims["sub"])


class JWTTokenServiceAdapter(TokenService):
    """
    Adapter between JWTService (Infra) and the port TokenService (Application)
    """

    def __init__(self, service: JWTService | None = None) -> None:
        self._service = service or JWTService()

    def create_access_token(
        self,
        subject: str,
        extra: Mapping[str, object] | None = None,
    ) -> str:
        return self._service.create_access_token(subject, extra)

    def create_refresh_token(
        self,
        subject: str,
        extra: Mapping[str, object] | None = None,
    ) -> str:
        return self._service.create_refresh_token(subject, extra)

    def decode_token(self, token: str) -> Mapping[str, object]:
        return self._service.decode_token(token)

    def validate_refresh_token(self, token: str) -> str:
        return self._service.validate_refresh_token(token)
