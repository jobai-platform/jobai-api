from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from app.application.auth.ports import RefreshTokenRepository, TokenService
from app.application.users.ports import PasswordHasher, UserRepository
from app.domain.common.exceptions import UnauthorizedError
from app.domain.users.entities import User
from app.domain.users.value_objects import Email


@dataclass
class TokenPair:
    access_token: str
    refresh_token: str
    token_type: str = "Bearer"


@dataclass(frozen=True)
class RefreshTokenClaims:
    subject: UUID
    jti: str
    expires_at: datetime


def _unauthorized() -> None:
    raise UnauthorizedError(
        code="invalid_authentication",
        details="Invalid refresh token",
    )


def _expires_at_from_claim(value: object) -> datetime:
    if isinstance(value, datetime):
        expires_at = value
    elif isinstance(value, int | float):
        expires_at = datetime.fromtimestamp(value, tz=UTC)
    else:
        _unauthorized()

    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=UTC)
    return expires_at


def _parse_refresh_claims(claims: Mapping[str, object]) -> RefreshTokenClaims:
    if claims.get("type") != "refresh":
        _unauthorized()

    subject = claims.get("sub")
    jti = claims.get("jti")
    exp = claims.get("exp")
    if not subject or not isinstance(jti, str) or not jti:
        _unauthorized()

    try:
        user_id = UUID(str(subject))
        expires_at = _expires_at_from_claim(exp)
    except (TypeError, ValueError):
        _unauthorized()

    if expires_at <= datetime.now(UTC):
        _unauthorized()

    return RefreshTokenClaims(subject=user_id, jti=jti, expires_at=expires_at)


def _decode_refresh_token(token_service: TokenService, refresh_token: str) -> RefreshTokenClaims:
    try:
        claims = token_service.decode_token(refresh_token)
    except Exception:
        _unauthorized()
    return _parse_refresh_claims(claims)


def _token_extra_from_user(user: User) -> dict[str, str]:
    return {
        "role": user.role,
        "email": str(user.email),
    }


class AuthService:
    """
    Service for handling authentication-related use cases.
    """
    def __init__(
        self,
        user_repo: UserRepository,
        pwd_hasher: PasswordHasher,
        token_service: TokenService,
    ) -> None:
        self.user_repo = user_repo
        self.pwd_hasher = pwd_hasher
        self.token_service = token_service


    async def login(self, email: str | Email, password: str) -> TokenPair:
        """
        Authenticate a user and return auth tokens.
        :param email: email of the user
        :param password: password of the user
        :return: AuthTokens object containing access and refresh tokens
        """
        email_vo = email if isinstance(email, Email) else Email.from_raw(email)

        user: User | None = await self.user_repo.get_by_email(email_vo)
        if (not user or
            not user.hashed_password or
            not self.pwd_hasher.verify(password, user.hashed_password)
        ):
            raise ValueError("Invalid credentials")

        if not user.is_active:
            raise ValueError("User account is inactive")

        subject = str(user.id)
        extra = {
            "role": user.role,
            "email": str(user.email),
        }

        access_token = self.token_service.create_access_token(
            subject=subject,
            extra=extra,
        )
        refresh_token = self.token_service.create_refresh_token(
            subject=subject,
            extra=extra,
        )

        return TokenPair(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="Bearer",
        )


class RefreshTokenUseCase:
    def __init__(
        self,
        user_repo: UserRepository,
        token_service: TokenService,
        refresh_token_repo: RefreshTokenRepository,
    ) -> None:
        self._user_repo = user_repo
        self._token_service = token_service
        self._refresh_token_repo = refresh_token_repo

    async def execute(self, refresh_token: str) -> TokenPair:
        old_claims = _decode_refresh_token(self._token_service, refresh_token)
        if await self._refresh_token_repo.is_revoked(old_claims.jti):
            _unauthorized()

        user = await self._user_repo.get_by_id(old_claims.subject)
        if not user or not user.is_active:
            _unauthorized()

        await self._refresh_token_repo.revoke(old_claims.jti)

        subject = str(user.id)
        extra = _token_extra_from_user(user)
        new_access_token = self._token_service.create_access_token(subject=subject, extra=extra)
        new_refresh_token = self._token_service.create_refresh_token(subject=subject, extra=extra)
        new_claims = _decode_refresh_token(self._token_service, new_refresh_token)

        await self._refresh_token_repo.persist(
            jti=new_claims.jti,
            user_id=new_claims.subject,
            expires_at=new_claims.expires_at,
        )

        return TokenPair(
            access_token=new_access_token,
            refresh_token=new_refresh_token,
            token_type="Bearer",
        )


class LogoutUseCase:
    def __init__(
        self,
        token_service: TokenService,
        refresh_token_repo: RefreshTokenRepository,
    ) -> None:
        self._token_service = token_service
        self._refresh_token_repo = refresh_token_repo

    async def execute(self, refresh_token: str) -> None:
        try:
            claims = _decode_refresh_token(self._token_service, refresh_token)
            await self._refresh_token_repo.revoke(claims.jti)
        except Exception:
            return None
