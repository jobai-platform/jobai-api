from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
import hashlib
from uuid import UUID, uuid4

from app.application.auth.ports import RefreshTokenRepository, TokenService
from app.application.billing.ports import SubscriptionRepository
from app.application.users.ports import PasswordHasher, UserRepository
from app.application.users.use_cases import CandidateService
from app.domain.billing.entities.subscription import Subscription
from app.domain.common.exceptions import UnauthorizedError
from app.domain.users.entities import Candidate
from app.domain.users.refresh_token import RefreshToken
from app.domain.users.value_objects import Email


@dataclass
class TokenPair:
    access_token: str
    refresh_token: str
    token_type: str = "Bearer"


@dataclass(frozen=True)
class LinkedInAuthResult:
    access_token: str
    refresh_token: str
    is_new_user: bool
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


def _token_extra_from_user(user: Candidate) -> dict[str, str]:
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

        user: Candidate | None = await self.user_repo.get_by_email(email_vo)
        if (not user or
            not user.hashed_password or
            not self.pwd_hasher.verify(password, user.hashed_password.value)
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

        token_hash = hashlib.sha256(refresh_token.encode()).hexdigest()
        stored = await self._refresh_token_repo.find_by_token_hash(token_hash)
        if stored is None or stored.is_revoked:
            _unauthorized()

        user = await self._user_repo.get_by_id(old_claims.subject)
        if not user or not user.is_active:
            _unauthorized()

        await self._refresh_token_repo.revoke(token_hash)

        subject = str(user.id)
        extra = _token_extra_from_user(user)
        new_access_token = self._token_service.create_access_token(subject=subject, extra=extra)
        new_refresh_token = self._token_service.create_refresh_token(subject=subject, extra=extra)
        new_claims = _decode_refresh_token(self._token_service, new_refresh_token)

        new_hash = hashlib.sha256(new_refresh_token.encode()).hexdigest()
        await self._refresh_token_repo.save(RefreshToken(
            id=uuid4(),
            token_hash=new_hash,
            user_id=new_claims.subject,
            expires_at=new_claims.expires_at,
        ))

        return TokenPair(
            access_token=new_access_token,
            refresh_token=new_refresh_token,
            token_type="Bearer",
        )


class LogoutUseCase:
    def __init__(
        self,
        refresh_token_repo: RefreshTokenRepository,
    ) -> None:
        self._refresh_token_repo = refresh_token_repo

    async def execute(self, refresh_token: str) -> None:
        try:
            token_hash = hashlib.sha256(refresh_token.encode()).hexdigest()
            await self._refresh_token_repo.revoke(token_hash)
        except Exception:
            return None


@dataclass(slots=True)
class RegisterResult:
    candidate: Candidate
    tokens: TokenPair


class RegisterUseCase:
    def __init__(
        self,
        user_service: CandidateService,
        token_service: TokenService,
        refresh_token_repo: RefreshTokenRepository,
        subscription_repo: SubscriptionRepository,
    ) -> None:
        self._user_service = user_service
        self._token_service = token_service
        self._refresh_token_repo = refresh_token_repo
        self._subscription_repo = subscription_repo

    async def execute(
        self,
        *,
        email: str,
        password: str,
        first_name: str,
        last_name: str,
    ) -> RegisterResult:
        candidate = await self._user_service.register(
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name,
        )
        # Both operations share the same SQLAlchemy session (injected via DI).
        # A failure here rolls back the user creation too — atomicity is guaranteed
        # by the session-scoped transaction, not by application code.
        await self._subscription_repo.create(Subscription.create_freemium(user_id=candidate.id))
        tokens = self._issue_tokens(candidate)
        await self._persist_refresh_token(candidate.id, tokens.refresh_token)
        return RegisterResult(candidate=candidate, tokens=tokens)

    def _issue_tokens(self, user: Candidate) -> TokenPair:
        subject = str(user.id)
        extra = _token_extra_from_user(user)
        return TokenPair(
            access_token=self._token_service.create_access_token(subject, extra),
            refresh_token=self._token_service.create_refresh_token(subject, extra),
        )

    async def _persist_refresh_token(self, user_id: UUID, refresh_token: str) -> None:
        token_hash = hashlib.sha256(refresh_token.encode()).hexdigest()
        claims = _decode_refresh_token(self._token_service, refresh_token)
        await self._refresh_token_repo.save(RefreshToken(
            id=uuid4(),
            token_hash=token_hash,
            user_id=claims.subject,
            expires_at=claims.expires_at,
        ))
