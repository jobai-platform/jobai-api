from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from app.application.auth.ports import RefreshTokenRepository
from app.application.auth.use_cases import LogoutUseCase
from app.domain.users.entities import RefreshToken


class FakeRefreshTokenRepository(RefreshTokenRepository):
    def __init__(self, *, fail_on_revoke: bool = False) -> None:
        self.fail_on_revoke = fail_on_revoke
        self._store: dict[str, RefreshToken] = {}

    def seed(self, token_raw: str, *, user_id=None, revoked: bool = False) -> str:
        from hashlib import sha256
        token_hash = sha256(token_raw.encode()).hexdigest()
        self._store[token_hash] = RefreshToken(
            token_hash=token_hash,
            user_id=user_id or uuid4(),
            expires_at=datetime.now(UTC) + timedelta(days=7),
            revoked_at=datetime.now(UTC) if revoked else None,
        )
        return token_hash

    async def save(self, token: RefreshToken) -> None:
        self._store[token.token_hash] = token

    async def find_by_token_hash(self, token_hash: str) -> RefreshToken | None:
        return self._store.get(token_hash)

    async def revoke(self, token_hash: str) -> None:
        if self.fail_on_revoke:
            raise RuntimeError("database unavailable")
        token = self._store.get(token_hash)
        if token is not None and token.revoked_at is None:
            token.revoked_at = datetime.now(UTC)


@pytest.mark.asyncio
async def test_logout_revokes_current_refresh_token() -> None:
    refresh_repo = FakeRefreshTokenRepository()
    token_hash = refresh_repo.seed("refresh-token")
    use_case = LogoutUseCase(refresh_token_repo=refresh_repo)

    await use_case.execute("refresh-token")

    stored = refresh_repo._store.get(token_hash)
    assert stored is not None
    assert stored.revoked_at is not None


@pytest.mark.asyncio
async def test_logout_does_not_propagate_repository_failure() -> None:
    refresh_repo = FakeRefreshTokenRepository(fail_on_revoke=True)
    refresh_repo.seed("refresh-token")
    use_case = LogoutUseCase(refresh_token_repo=refresh_repo)

    await use_case.execute("refresh-token")


@pytest.mark.asyncio
async def test_logout_with_unknown_token_is_graceful() -> None:
    refresh_repo = FakeRefreshTokenRepository()
    use_case = LogoutUseCase(refresh_token_repo=refresh_repo)

    await use_case.execute("not-a-known-token")
