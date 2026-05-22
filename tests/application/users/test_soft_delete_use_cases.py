import pytest
from unittest.mock import AsyncMock
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from app.application.users.use_cases import UserService
from app.domain.users.entities import Candidate
from app.domain.users.value_objects import Email
from app.domain.common.deletion import DeletionInfo


@pytest.mark.asyncio
async def test_soft_delete_use_case_calls_repo_soft_delete():
    user_id = uuid4()
    email = Email.from_raw("user@example.com")

    fake_repo = AsyncMock()
    fake_repo.get_by_id.return_value = Candidate(id=user_id, email=email)
    fake_repo.soft_delete = AsyncMock()

    service = UserService(user_repo=fake_repo, pwd_hasher=AsyncMock())

    await service.delete_user(user_id)

    fake_repo.get_by_id.assert_awaited_with(user_id)
    assert fake_repo.soft_delete.await_count == 1


@pytest.mark.asyncio
async def test_restore_use_case_calls_repo_restore_only_if_deleted():
    user_id = uuid4()
    email = Email.from_raw("user2@example.com")

    deleted_info = DeletionInfo(is_deleted=True, deleted_at=datetime.now(timezone.utc), scheduled_purge_at=datetime.now(timezone.utc) + timedelta(days=365))
    deleted_user = Candidate(id=user_id, email=email)
    deleted_user.deletion = deleted_info

    fake_repo = AsyncMock()
    fake_repo.get_by_id.return_value = deleted_user
    fake_repo.restore = AsyncMock()

    service = UserService(user_repo=fake_repo, pwd_hasher=AsyncMock())

    await service.restore_user(user_id)

    fake_repo.restore.assert_awaited_with(user_id)


@pytest.mark.asyncio
async def test_purge_use_case_calls_repo_purge_and_returns_count():
    fake_repo = AsyncMock()
    fake_repo.purge_older_than = AsyncMock(return_value=5)

    service = UserService(user_repo=fake_repo, pwd_hasher=AsyncMock())

    cutoff = datetime.now(timezone.utc) - timedelta(days=365)
    deleted = await service.purge_users_older_than(cutoff)

    fake_repo.purge_older_than.assert_awaited_with(cutoff)
    assert deleted == 5

