import pytest

from app.application.users.use_cases import UserService
from app.domain.users.value_objects import Email
from tests.fakes.users.in_memory_user_repo import InMemoryUserRepository


class DummyHashingService:
    @staticmethod
    def hash_password(raw_password: str) -> str:
        return f"hashed_{raw_password}"

    @staticmethod
    def verify_password(raw_password: str, hashed_password: str) -> bool:
        return hashed_password == f"hashed_{raw_password}"


@pytest.mark.asyncio
async def test_register_creates_user_with_hashed_password():
    user_repo = InMemoryUserRepository()
    hashing_service = DummyHashingService()
    service = UserService(user_repo=user_repo, pwd_hasher=hashing_service)

    user = await service.register(
        email="user@example.com",
        password="securepassword",
        username="testuser",
    )

    assert user.id is not None
    assert isinstance(user.email, Email)
    assert str(user.email) == "user@example.com"
    assert user.hashed_password == "hashed_securepassword"
    assert user.role == "user"
    assert user.is_active is True

@pytest.mark.asyncio
async def test_register_fails_if_email_already_exists_normalized():
    user_repo = InMemoryUserRepository()
    hashing_service = DummyHashingService()
    service = UserService(user_repo=user_repo, pwd_hasher=hashing_service)

    await service.register(email="USER@example.com", password="secret")

    with pytest.raises(ValueError):
        await service.register(email="  user@EXAMPLE.com  ", password="other")

@pytest.mark.asyncio
async def test_register_allows_user_without_password():
    user_repo = InMemoryUserRepository()
    hashing_service = DummyHashingService()
    service = UserService(user_repo=user_repo, pwd_hasher=hashing_service)

    user = await service.register(
        email="nopass@example.com",
        password=None,
    )

    assert user.hashed_password is None
    assert str(user.email) == "nopass@example.com"

