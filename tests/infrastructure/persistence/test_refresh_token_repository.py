import uuid
from datetime import UTC, datetime, timedelta

import pytest
import pytest_asyncio
from sqlalchemy.exc import IntegrityError

from app.infrastructure.persistence.models.user import UserModel
from app.infrastructure.persistence.repositories.refresh_token_sqlalchemy import (
    SQLAlchemyRefreshTokenRepository,
)


@pytest_asyncio.fixture
async def seeded_user(db_session):
    user = UserModel(
        email=f"rt-{uuid.uuid4().hex[:8]}@example.com",
        hashed_password="fakehashed",
        role="user",
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()
    return user


@pytest.mark.asyncio
async def test_is_revoked_returns_true_for_unknown_jti(db_session) -> None:
    repo = SQLAlchemyRefreshTokenRepository(db_session)

    result = await repo.is_revoked("jti-that-does-not-exist")

    assert result is True


@pytest.mark.asyncio
async def test_is_revoked_returns_true_for_expired_token(db_session, seeded_user) -> None:
    repo = SQLAlchemyRefreshTokenRepository(db_session)
    jti = f"expired-{uuid.uuid4().hex}"
    await repo.persist(
        jti=jti,
        user_id=seeded_user.id,
        expires_at=datetime.now(UTC) - timedelta(seconds=1),
    )

    result = await repo.is_revoked(jti)

    assert result is True


@pytest.mark.asyncio
async def test_revoke_is_idempotent(db_session, seeded_user) -> None:
    repo = SQLAlchemyRefreshTokenRepository(db_session)
    jti = f"idem-{uuid.uuid4().hex}"
    await repo.persist(jti=jti, user_id=seeded_user.id, expires_at=datetime.now(UTC) + timedelta(days=7))

    await repo.revoke(jti)
    await repo.revoke(jti)

    assert await repo.is_revoked(jti) is True


@pytest.mark.asyncio
async def test_persist_duplicate_jti_raises(db_session, seeded_user) -> None:
    repo = SQLAlchemyRefreshTokenRepository(db_session)
    jti = f"dup-{uuid.uuid4().hex}"
    expires = datetime.now(UTC) + timedelta(days=7)
    await repo.persist(jti=jti, user_id=seeded_user.id, expires_at=expires)

    with pytest.raises(IntegrityError):
        await repo.persist(jti=jti, user_id=seeded_user.id, expires_at=expires)
