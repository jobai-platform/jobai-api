from collections.abc import Mapping
from datetime import UTC, datetime, timedelta, timezone
from typing import Optional
from uuid import UUID, uuid4

import pytest

from app.application.auth.ports import RefreshTokenRepository, TokenService
from app.application.auth.use_cases import LogoutUseCase


class FakeRefreshTokenRepository(RefreshTokenRepository):
    def __init__(self, *, fail_on_revoke: bool = False) -> None:
        self.fail_on_revoke = fail_on_revoke
        self.revoked_jtis: set[str] = set()

    async def is_revoked(self, jti: str) -> bool:
        return jti in self.revoked_jtis

    async def revoke(self, jti: str) -> None:
        if self.fail_on_revoke:
            raise RuntimeError("database unavailable")
        self.revoked_jtis.add(jti)

    async def persist(self, *, jti: str, user_id: UUID, expires_at: datetime) -> None:
        return None


class FakeTokenService(TokenService):
    def __init__(self) -> None:
        self._claims_by_token: dict[str, dict] = {}

    def add_refresh_token(self, token: str, *, subject: str | None = None, jti: str = "refresh-jti") -> None:
        self._claims_by_token[token] = {
            "sub": subject or str(uuid4()),
            "type": "refresh",
            "jti": jti,
            "exp": datetime.now(UTC) + timedelta(days=7),
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
        return f"refresh-token-for-{subject}"

    def decode_token(self, token: str) -> Mapping[str, object]:
        return self._claims_by_token[token]


@pytest.mark.asyncio
async def test_logout_revokes_current_refresh_token() -> None:
    token_service = FakeTokenService()
    token_service.add_refresh_token("refresh-token", jti="current-jti")
    refresh_repo = FakeRefreshTokenRepository()
    use_case = LogoutUseCase(token_service=token_service, refresh_token_repo=refresh_repo)

    await use_case.execute("refresh-token")

    assert "current-jti" in refresh_repo.revoked_jtis


@pytest.mark.asyncio
async def test_logout_does_not_propagate_repository_failure() -> None:
    token_service = FakeTokenService()
    token_service.add_refresh_token("refresh-token", jti="current-jti")
    refresh_repo = FakeRefreshTokenRepository(fail_on_revoke=True)
    use_case = LogoutUseCase(token_service=token_service, refresh_token_repo=refresh_repo)

    await use_case.execute("refresh-token")
