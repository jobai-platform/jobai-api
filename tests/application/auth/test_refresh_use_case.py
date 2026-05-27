from collections.abc import Mapping
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from uuid import UUID, uuid4

import pytest

from app.application.auth.ports import RefreshTokenRepository, TokenService
from app.application.auth.use_cases import RefreshTokenUseCase, TokenPair
from app.domain.common.exceptions import UnauthorizedError
from app.domain.users.entities import Candidate, CandidateRole
from app.domain.users.refresh_token import RefreshToken
from app.domain.users.value_objects import Email
from tests.fakes.users.in_memory_user_repo import InMemoryUserRepository


class FakeRefreshTokenRepository(RefreshTokenRepository):
    def __init__(self) -> None:
        self._store: dict[str, RefreshToken] = {}

    def seed(
        self,
        token_raw: str,
        *,
        user_id: UUID,
        expires_at: datetime | None = None,
        revoked: bool = False,
    ) -> str:
        token_hash = sha256(token_raw.encode()).hexdigest()
        self._store[token_hash] = RefreshToken(
            id=uuid4(),
            token_hash=token_hash,
            user_id=user_id,
            expires_at=expires_at or datetime.now(UTC) + timedelta(days=7),
            revoked_at=datetime.now(UTC) if revoked else None,
        )
        return token_hash

    async def save(self, token: RefreshToken) -> None:
        self._store[token.token_hash] = token

    async def find_by_token_hash(self, token_hash: str) -> RefreshToken | None:
        return self._store.get(token_hash)

    async def revoke(self, token_hash: str) -> None:
        token = self._store.get(token_hash)
        if token is not None and token.revoked_at is None:
            token.revoked_at = datetime.now(UTC)


class FakeTokenService(TokenService):
    def __init__(self) -> None:
        self._claims_by_token: dict[str, dict] = {}
        self._refresh_count = 0

    def add_refresh_token(
        self,
        token: str,
        *,
        subject: str,
        jti: str,
        expires_at: datetime | None = None,
    ) -> None:
        self._claims_by_token[token] = {
            "sub": subject,
            "type": "refresh",
            "jti": jti,
            "exp": expires_at or datetime.now(UTC) + timedelta(days=7),
        }

    def create_access_token(
        self,
        subject: str,
        extra: Mapping[str, object] | None = None,
    ) -> str:
        return f"access-token-for-{subject}"

    def create_refresh_token(
        self,
        subject: str,
        extra: Mapping[str, object] | None = None,
    ) -> str:
        self._refresh_count += 1
        token = f"refresh-token-{self._refresh_count}-for-{subject}"
        self._claims_by_token[token] = {
            "sub": subject,
            "type": "refresh",
            "jti": f"new-jti-{self._refresh_count}",
            "exp": datetime.now(UTC) + timedelta(days=7),
        }
        return token

    def decode_token(self, token: str) -> Mapping[str, object]:
        return self._claims_by_token[token]

    def validate_refresh_token(self, token: str) -> str:
        claims = self._claims_by_token.get(token)
        if not claims or claims.get("type") != "refresh":
            raise UnauthorizedError(code="invalid_token", details="Invalid refresh token")
        return str(claims["sub"])


@pytest.mark.asyncio
async def test_refresh_raises_unauthorized_when_token_is_malformed() -> None:
    user_repo = InMemoryUserRepository()
    token_service = FakeTokenService()
    refresh_repo = FakeRefreshTokenRepository()
    use_case = RefreshTokenUseCase(
        user_repo=user_repo,
        token_service=token_service,
        refresh_token_repo=refresh_repo,
    )

    with pytest.raises(UnauthorizedError):
        await use_case.execute("not-a-valid-token")


@pytest.mark.asyncio
async def test_refresh_raises_unauthorized_when_token_is_expired() -> None:
    user_repo = InMemoryUserRepository()
    user = await user_repo.create(Candidate(id=uuid4(), email=Email.from_raw("user@example.com")))
    token_service = FakeTokenService()
    token_service.add_refresh_token(
        "expired-token",
        subject=str(user.id),
        jti="expired-jti",
        expires_at=datetime.now(UTC) - timedelta(seconds=1),
    )
    refresh_repo = FakeRefreshTokenRepository()
    use_case = RefreshTokenUseCase(
        user_repo=user_repo,
        token_service=token_service,
        refresh_token_repo=refresh_repo,
    )

    with pytest.raises(UnauthorizedError):
        await use_case.execute("expired-token")


@pytest.mark.asyncio
async def test_refresh_raises_unauthorized_when_user_is_inactive() -> None:
    user_repo = InMemoryUserRepository()
    user = await user_repo.create(
        Candidate(id=None, email=Email.from_raw("inactive@example.com"), is_active=False)
    )
    token_service = FakeTokenService()
    token_service.add_refresh_token("valid-token", subject=str(user.id), jti="active-jti")
    refresh_repo = FakeRefreshTokenRepository()
    refresh_repo.seed("valid-token", user_id=user.id)
    use_case = RefreshTokenUseCase(
        user_repo=user_repo,
        token_service=token_service,
        refresh_token_repo=refresh_repo,
    )

    with pytest.raises(UnauthorizedError):
        await use_case.execute("valid-token")


@pytest.mark.asyncio
async def test_refresh_token_raises_unauthorized_when_token_is_revoked() -> None:
    user_repo = InMemoryUserRepository()
    user = await user_repo.create(Candidate(id=uuid4(), email=Email.from_raw("user@example.com")))
    token_service = FakeTokenService()
    token_service.add_refresh_token("old-refresh-token", subject=str(user.id), jti="old-jti")
    refresh_repo = FakeRefreshTokenRepository()
    refresh_repo.seed("old-refresh-token", user_id=user.id, revoked=True)
    use_case = RefreshTokenUseCase(
        user_repo=user_repo,
        token_service=token_service,
        refresh_token_repo=refresh_repo,
    )

    with pytest.raises(UnauthorizedError):
        await use_case.execute("old-refresh-token")


@pytest.mark.asyncio
async def test_refresh_raises_unauthorized_when_token_not_in_store() -> None:
    user_repo = InMemoryUserRepository()
    user = await user_repo.create(Candidate(id=uuid4(), email=Email.from_raw("user@example.com")))
    token_service = FakeTokenService()
    token_service.add_refresh_token("unknown-token", subject=str(user.id), jti="some-jti")
    refresh_repo = FakeRefreshTokenRepository()
    use_case = RefreshTokenUseCase(
        user_repo=user_repo,
        token_service=token_service,
        refresh_token_repo=refresh_repo,
    )

    with pytest.raises(UnauthorizedError):
        await use_case.execute("unknown-token")


@pytest.mark.asyncio
async def test_refresh_token_rotates_old_token_and_persists_new_token() -> None:
    user_repo = InMemoryUserRepository()
    user = await user_repo.create(
        Candidate(
            id=uuid4(),
            email=Email.from_raw("user@example.com"),
            role=CandidateRole.USER,
            is_active=True,
        ),
    )
    token_service = FakeTokenService()
    token_service.add_refresh_token("old-refresh-token", subject=str(user.id), jti="old-jti")
    refresh_repo = FakeRefreshTokenRepository()
    old_hash = refresh_repo.seed("old-refresh-token", user_id=user.id)
    use_case = RefreshTokenUseCase(
        user_repo=user_repo,
        token_service=token_service,
        refresh_token_repo=refresh_repo,
    )

    result = await use_case.execute("old-refresh-token")

    assert isinstance(result, TokenPair)
    assert result.access_token == f"access-token-for-{user.id}"
    assert result.refresh_token == f"refresh-token-1-for-{user.id}"

    # Old token revoked
    assert refresh_repo._store[old_hash].revoked_at is not None

    # New token persisted
    new_hash = sha256(result.refresh_token.encode()).hexdigest()
    assert new_hash in refresh_repo._store
    new_stored = refresh_repo._store[new_hash]
    assert new_stored.user_id == user.id
    assert new_stored.expires_at > datetime.now(UTC)
