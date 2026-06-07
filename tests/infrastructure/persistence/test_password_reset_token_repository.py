from datetime import UTC, datetime, timedelta
import hashlib
import uuid

import pytest

from app.infrastructure.persistence.models.user import UserModel
from app.infrastructure.persistence.repositories.password_reset_token_sqlalchemy import (
    SQLAlchemyPasswordResetTokenRepository,
)


@pytest.mark.asyncio
async def test_password_reset_token_repository_saves_and_finds_record(db_session) -> None:
    candidate = UserModel(
        email=f"reset-{uuid.uuid4().hex[:8]}@example.com",
        hashed_password="old-hash",
        role="user",
        is_active=True,
    )
    db_session.add(candidate)
    await db_session.flush()
    repo = SQLAlchemyPasswordResetTokenRepository(db_session)
    created_at = datetime.now(UTC)
    token_hash = hashlib.sha256(uuid.uuid4().bytes).hexdigest()

    await repo.save(candidate_id=candidate.id, token_hash=token_hash, created_at=created_at)

    found = await repo.find_by_token_hash(token_hash)
    assert found is not None
    assert found.candidate_id == candidate.id
    assert found.token_hash == token_hash
    assert found.created_at == created_at
    assert found.consumed_at is None


@pytest.mark.asyncio
async def test_password_reset_token_repository_returns_none_for_unknown_hash(db_session) -> None:
    repo = SQLAlchemyPasswordResetTokenRepository(db_session)

    assert await repo.find_by_token_hash("0" * 64) is None


@pytest.mark.asyncio
async def test_password_reset_token_repository_consumes_token_only_once(db_session) -> None:
    candidate = UserModel(
        email=f"claim-{uuid.uuid4().hex[:8]}@example.com",
        hashed_password="old-hash",
        role="user",
        is_active=True,
    )
    db_session.add(candidate)
    await db_session.flush()
    repo = SQLAlchemyPasswordResetTokenRepository(db_session)
    created_at = datetime.now(UTC)
    consumed_at = created_at + timedelta(minutes=5)
    token_hash = hashlib.sha256(uuid.uuid4().bytes).hexdigest()
    await repo.save(candidate_id=candidate.id, token_hash=token_hash, created_at=created_at)

    first_claim = await repo.consume_if_available(token_hash, consumed_at=consumed_at)
    second_claim = await repo.consume_if_available(
        token_hash,
        consumed_at=consumed_at + timedelta(seconds=1),
    )

    assert first_claim is True
    assert second_claim is False
    found = await repo.find_by_token_hash(token_hash)
    assert found is not None
    assert found.consumed_at == consumed_at


@pytest.mark.asyncio
async def test_password_reset_token_repository_cannot_consume_unknown_hash(db_session) -> None:
    repo = SQLAlchemyPasswordResetTokenRepository(db_session)

    consumed = await repo.consume_if_available("0" * 64, consumed_at=datetime.now(UTC))

    assert consumed is False
