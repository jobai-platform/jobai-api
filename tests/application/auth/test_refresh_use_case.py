from collections.abc import Mapping
from datetime import UTC, datetime, timedelta, timezone
from typing import Optional
from uuid import UUID

import pytest

from app.application.auth.ports import RefreshTokenRepository, TokenService
from app.application.auth.use_cases import RefreshTokenUseCase, TokenPair
from app.domain.common.exceptions import UnauthorizedError
from app.domain.users.entities import User
from app.domain.users.value_objects import Email
from tests.fakes.users.in_memory_user_repo import InMemoryUserRepository


class FakeRefreshTokenRepository(RefreshTokenRepository):
    def __init__(self) -> None:
        self.revoked_jtis: set[str] = set()
        self.persisted_tokens: dict[str, tuple[UUID, datetime]] = {}

    async def is_revoked(self, jti: str) -> bool:
        return jti in self.revoked_jtis

    async def revoke(self, jti: str) -> None:
        self.revoked_jtis.add(jti)

    async def persist(self, *, jti: str, user_id: UUID, expires_at: datetime) -> None:
        self.persisted_tokens[jti] = (user_id, expires_at)


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


@pytest.mark.asyncio
async def test_refresh_token_raises_unauthorized_when_token_is_revoked() -> None:
    user_repo = InMemoryUserRepository()
    user = await user_repo.create(User(id=None, email=Email.from_raw("user@example.com")))
    token_service = FakeTokenService()
    token_service.add_refresh_token("old-refresh-token", subject=str(user.id), jti="old-jti")
    refresh_repo = FakeRefreshTokenRepository()
    refresh_repo.revoked_jtis.add("old-jti")
    use_case = RefreshTokenUseCase(
        user_repo=user_repo,
        token_service=token_service,
        refresh_token_repo=refresh_repo,
    )

    with pytest.raises(UnauthorizedError):
        await use_case.execute("old-refresh-token")


@pytest.mark.asyncio
async def test_refresh_token_rotates_old_token_and_persists_new_token() -> None:
    user_repo = InMemoryUserRepository()
    user = await user_repo.create(
        User(
            id=None,
            email=Email.from_raw("user@example.com"),
            role="user",
            is_active=True,
        ),
    )
    token_service = FakeTokenService()
    token_service.add_refresh_token("old-refresh-token", subject=str(user.id), jti="old-jti")
    refresh_repo = FakeRefreshTokenRepository()
    use_case = RefreshTokenUseCase(
        user_repo=user_repo,
        token_service=token_service,
        refresh_token_repo=refresh_repo,
    )

    result = await use_case.execute("old-refresh-token")

    assert isinstance(result, TokenPair)
    assert result.access_token == f"access-token-for-{user.id}"
    assert result.refresh_token == f"refresh-token-1-for-{user.id}"
    assert "old-jti" in refresh_repo.revoked_jtis
    assert "new-jti-1" in refresh_repo.persisted_tokens
    persisted_user_id, expires_at = refresh_repo.persisted_tokens["new-jti-1"]
    assert persisted_user_id == user.id
    assert expires_at > datetime.now(UTC)
