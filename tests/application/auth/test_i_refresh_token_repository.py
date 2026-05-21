"""
Tests TDD pour IRefreshTokenRepository port (validated via InMemoryIRefreshTokenRepository)
Bounded Context : users-auth
Layer : application
"""
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from app.domain.users.refresh_token import RefreshToken
from tests.fakes.auth.in_memory_refresh_token_repo import InMemoryIRefreshTokenRepository


def _make_token(*, expires_in_days: int = 7, revoked: bool = False) -> RefreshToken:
    return RefreshToken(
        id=uuid4(),
        token_hash=f"hash-{uuid4().hex}",
        user_id=uuid4(),
        expires_at=datetime.now(UTC) + timedelta(days=expires_in_days),
        revoked_at=datetime.now(UTC) if revoked else None,
    )


class TestSave:

    @pytest.mark.asyncio
    async def test_save_persists_token(self) -> None:
        """Saved token can be retrieved by its hash."""
        repo = InMemoryIRefreshTokenRepository()
        token = _make_token()

        await repo.save(token)

        found = await repo.find_by_token_hash(token.token_hash)
        assert found is not None
        assert found.token_hash == token.token_hash
        assert found.user_id == token.user_id


class TestFindByTokenHash:

    @pytest.mark.asyncio
    async def test_returns_none_for_unknown_hash(self) -> None:
        """Returns None when the hash has never been saved."""
        repo = InMemoryIRefreshTokenRepository()

        result = await repo.find_by_token_hash("nonexistent-hash")

        assert result is None

    @pytest.mark.asyncio
    async def test_returns_token_after_save(self) -> None:
        """Returns the exact token that was saved."""
        repo = InMemoryIRefreshTokenRepository()
        token = _make_token()
        await repo.save(token)

        result = await repo.find_by_token_hash(token.token_hash)

        assert result == token

    @pytest.mark.asyncio
    async def test_returns_revoked_token(self) -> None:
        """A revoked token is still findable — callers check is_valid."""
        repo = InMemoryIRefreshTokenRepository()
        token = _make_token(revoked=True)
        await repo.save(token)

        result = await repo.find_by_token_hash(token.token_hash)

        assert result is not None
        assert result.is_revoked is True


class TestRevoke:

    @pytest.mark.asyncio
    async def test_revoke_marks_token_as_revoked(self) -> None:
        """After revoke, find_by_token_hash returns a revoked token."""
        repo = InMemoryIRefreshTokenRepository()
        token = _make_token()
        await repo.save(token)

        await repo.revoke(token.token_hash)

        found = await repo.find_by_token_hash(token.token_hash)
        assert found is not None
        assert found.is_revoked is True

    @pytest.mark.asyncio
    async def test_revoke_is_idempotent(self) -> None:
        """Revoking the same token twice does not raise."""
        repo = InMemoryIRefreshTokenRepository()
        token = _make_token()
        await repo.save(token)

        await repo.revoke(token.token_hash)
        await repo.revoke(token.token_hash)

        found = await repo.find_by_token_hash(token.token_hash)
        assert found is not None
        assert found.is_revoked is True

    @pytest.mark.asyncio
    async def test_revoke_unknown_hash_does_not_raise(self) -> None:
        """Revoking a hash that was never saved is a no-op."""
        repo = InMemoryIRefreshTokenRepository()

        await repo.revoke("never-saved-hash")
