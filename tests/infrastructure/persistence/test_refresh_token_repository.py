"""
Tests TDD pour SQLAlchemyRefreshTokenRepository
Bounded Context : users-auth
Layer : infrastructure
"""
from datetime import UTC, datetime, timedelta
import uuid

import pytest
import pytest_asyncio
from sqlalchemy import delete
from sqlalchemy.exc import IntegrityError

from app.domain.users.refresh_token import RefreshToken
from app.infrastructure.persistence.models.user import UserModel
from app.infrastructure.persistence.repositories.refresh_token_sqlalchemy import (
    SQLAlchemyRefreshTokenRepository,
)


@pytest_asyncio.fixture
async def seeded_user(db_session):
    user = UserModel(
        email=f"irt-{uuid.uuid4().hex[:8]}@example.com",
        hashed_password="fakehashed",
        role="user",
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()
    return user


def _make_token(user_id: uuid.UUID, *, expires_in_days: int = 7) -> RefreshToken:
    return RefreshToken(
        id=uuid.uuid4(),
        token_hash=f"hash-{uuid.uuid4().hex}",
        user_id=user_id,
        expires_at=datetime.now(UTC) + timedelta(days=expires_in_days),
    )


@pytest.mark.asyncio
async def test_save_and_find_by_token_hash(db_session, seeded_user) -> None:
    """Saved token can be retrieved by token_hash."""
    repo = SQLAlchemyRefreshTokenRepository(db_session)
    token = _make_token(seeded_user.id)

    await repo.save(token)

    found = await repo.find_by_token_hash(token.token_hash)
    assert found is not None
    assert found.token_hash == token.token_hash
    assert found.user_id == seeded_user.id
    assert found.is_revoked is False


@pytest.mark.asyncio
async def test_find_by_token_hash_returns_none_for_unknown(db_session) -> None:
    """Returns None for a hash that was never persisted."""
    repo = SQLAlchemyRefreshTokenRepository(db_session)

    result = await repo.find_by_token_hash("unknown-hash")

    assert result is None


@pytest.mark.asyncio
async def test_revoke_marks_token_revoked(db_session, seeded_user) -> None:
    """After revoke, found token has is_revoked=True."""
    repo = SQLAlchemyRefreshTokenRepository(db_session)
    token = _make_token(seeded_user.id)
    await repo.save(token)

    await repo.revoke(token.token_hash)

    found = await repo.find_by_token_hash(token.token_hash)
    assert found is not None
    assert found.is_revoked is True


@pytest.mark.asyncio
async def test_revoke_is_idempotent(db_session, seeded_user) -> None:
    """Revoking the same token twice does not raise."""
    repo = SQLAlchemyRefreshTokenRepository(db_session)
    token = _make_token(seeded_user.id)
    await repo.save(token)

    await repo.revoke(token.token_hash)
    await repo.revoke(token.token_hash)

    found = await repo.find_by_token_hash(token.token_hash)
    assert found is not None
    assert found.is_revoked is True


@pytest.mark.asyncio
async def test_revoke_unknown_hash_is_noop(db_session) -> None:
    """Revoking a never-saved hash does not raise."""
    repo = SQLAlchemyRefreshTokenRepository(db_session)

    await repo.revoke("ghost-hash")


@pytest.mark.asyncio
async def test_cascade_delete_removes_tokens_when_user_deleted(db_session, seeded_user) -> None:
    """Tokens are removed automatically when the owning user is deleted (FK CASCADE)."""
    repo = SQLAlchemyRefreshTokenRepository(db_session)
    token = _make_token(seeded_user.id)
    await repo.save(token)

    await db_session.execute(
        delete(UserModel).where(UserModel.id == seeded_user.id)
    )
    await db_session.commit()

    found = await repo.find_by_token_hash(token.token_hash)
    assert found is None


@pytest.mark.asyncio
async def test_expired_token_roundtrip_preserves_is_expired(db_session, seeded_user) -> None:
    """A token with expires_at in the past roundtrips correctly and is_expired returns True."""
    repo = SQLAlchemyRefreshTokenRepository(db_session)
    token = _make_token(seeded_user.id, expires_in_days=-1)
    await repo.save(token)

    found = await repo.find_by_token_hash(token.token_hash)
    assert found is not None
    assert found.is_expired is True


@pytest.mark.asyncio
async def test_save_duplicate_token_hash_raises_integrity_error(db_session, seeded_user) -> None:
    """Saving two tokens with the same token_hash violates the unique constraint."""
    repo = SQLAlchemyRefreshTokenRepository(db_session)
    token = _make_token(seeded_user.id)
    await repo.save(token)

    duplicate = RefreshToken(
        id=uuid.uuid4(),
        token_hash=token.token_hash,
        user_id=seeded_user.id,
        expires_at=token.expires_at,
    )

    with pytest.raises(IntegrityError):
        await repo.save(duplicate)
