import uuid
from dataclasses import dataclass
from datetime import timedelta, datetime, timezone
from typing import Optional, Any, Mapping

from fastapi import HTTPException, status, Depends
from fastapi.params import Security
from fastapi.security import OAuth2PasswordBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from passlib.context import CryptContext

from app.core.config import settings

SECRET_KEY = settings.SECRET_KEY
ALGORITHM = settings.ALGORITHM
ACCESS_TOKEN_EXPIRE_MINUTES = settings.ACCESS_TOKEN_EXPIRE_MINUTES


pwd_context = CryptContext(schemes=['bcrypt'], deprecated='auto')
oauth2_scheme = OAuth2PasswordBearer(tokenUrl='/api/v1/auth/token')


@dataclass(frozen=True)
class JWTSettings:
    secret: str
    algorithm: str = 'HS256'
    access_token_expire_minutes: int = 60
    refresh_token_expire_days: int = 7
    issuer: str = 'jobai-backend'
    audience: str = 'jobai-frontend'

class PasswordService:
    """Hash and verify passwords using bcrypt."""
    def hash_password(self, password: str) -> str:
        """Hash a password."""
        return pwd_context.hash(password)

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify a password against its hash."""
        return pwd_context.verify(plain_password, hashed_password)


class JWTService:
    """Service for creating and verifying JWT tokens."""
    def __init__(self, cfg: Optional[JWTSettings] = None) -> None:
        self.cfg = cfg or JWTSettings(
            secret=getattr(settings, "JWT_SECRET_KEY", settings.SECRET_KEY),
            algorithm=getattr(settings, "JWT_ALGORITHM", getattr(settings, "ALGORITHM", "HS256")),
            access_token_expire_minutes=getattr(settings, "ACCESS_TOKEN_EXPIRE_MINUTES", 60),
            refresh_token_expire_days=getattr(settings, "REFRESH_TOKEN_EXPIRE_DAYS", 7),
            issuer=getattr(settings, "JWT_ISSUER", "jobai-backend"),
            audience=getattr(settings, "JWT_AUDIENCE", "jobai-frontend"),
        )


    def _now(self) -> datetime:
        """Get the current UTC time."""
        return datetime.now(timezone.utc)


    def _base_claims(self, subject: str) -> dict[str, Any]:
        """Generate base JWT claims."""
        now = self._now()
        return {
            "sub": subject,
            "iss": self.cfg.issuer,
            "aud": self.cfg.audience,
            "iat": now,
            "nbf": now,
            "jti": str(uuid.uuid4()),
        }

    def _encode(self, claims: Mapping[str, Any]) -> str:
        """Encode JWT claims into a token."""
        return jwt.encode(claims, self.cfg.secret, algorithm=self.cfg.algorithm)


    def _decode(self, token: str) -> Mapping[str, Any]:
        """Decode and validate a JWT token."""
        return jwt.decode(
            token,
            self.cfg.secret,
            algorithms=[self.cfg.algorithm],
            issuer=self.cfg.issuer,
            audience=self.cfg.audience,
            options={"require": True, "require_iat": True, "require_nbf": True},
        )


    def create_access_token(self, subject: str, extra: Optional[Mapping[str, Any]] = None) -> str:
        """Create an access token with optional extra claims."""
        payload = self._base_claims(subject)

        if extra:
            payload.update(extra)
            payload["type"] = "access"
            payload["exp"] = int((self._now() + timedelta(minutes=self.cfg.access_token_expire_minutes)).timestamp())

        return self._encode(payload)


    def create_refresh_token(self, subject: str, extra: Optional[Mapping[str, Any]] = None) -> str:
        """Create a refresh token with optional extra claims."""
        payload = self._base_claims(subject)

        if extra:
            payload.update(extra)
            payload["type"] = "refresh"
            payload["exp"] = int((self._now() + timedelta(days=self.cfg.refresh_token_expire_days)).timestamp())

        return self._encode(payload)


    def decode_token(self, token: str) -> Mapping[str, Any]:
        """Decode and validate a JWT token."""
        return self._decode(token)


def get_password_service() -> PasswordService:
    return PasswordService()


def get_jwt_service() -> JWTService:
    return JWTService()


def auth_wrapper(
    auth: HTTPAuthorizationCredentials = Security(oauth2_scheme),
    jwt_service: JWTService = Depends(get_jwt_service)
) -> str:
    token = auth.credentials

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Invalid token or expired token.',
            headers={'WWW-Authenticate': 'Bearer'}
        )

    try:
        payload = jwt_service.decode_token(token)
        if payload.get('type') != 'access':
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail='Invalid token type.',
                headers={'WWW-Authenticate': 'Bearer'}
            )

        user_id = str(payload['sub'])
        return user_id
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f'Could not validate credentials: {str(e)}',
            headers={'WWW-Authenticate': 'Bearer'}
        )
