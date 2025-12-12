from typing import Optional, Mapping

import pytest

from app.application.auth.ports import TokenService
from app.application.auth.use_cases import AuthService
from app.domain.users.entities import User
from app.domain.users.value_objects import Email
from app.application.auth.use_cases import TokenPair
from tests.fakes.users.in_memory_user_repo import InMemoryUserRepository


class DummyPasswordHasher:
    @staticmethod
    def hash_password(password: str) -> str:
        return f"hashed-{password}"

    @staticmethod
    def verify(plain_password: str, hashed_password: str) -> bool:
        return hashed_password == f"hashed-{plain_password}"


class FakeTokenService(TokenService):
    def create_access_token(
        self,
        subject: str,
        extra: Optional[Mapping[str, any]] = None,
    ) -> str:
        return f"access-token-for-{subject}"

    def create_refresh_token(
        self,
        subject: str,
        extra: Optional[Mapping[str, any]] = None,
    ) -> str:
        return f"refresh-token-for-{subject}"

    def decode_token(self, token: str) -> dict:
        return {}


@pytest.mark.asyncio
async def test_login_success_returns_token_pair():
    user_repo = InMemoryUserRepository()
    pwd_hasher = DummyPasswordHasher()
    token_service = FakeTokenService()
    service = AuthService(
        user_repo=user_repo,
        pwd_hasher=pwd_hasher,
        token_service=token_service
    )

    # Create a user to login with
    user = await user_repo.create(
        User(
            id=None,
            email=Email.from_raw("user@example.com"),
            hashed_password=pwd_hasher.hash_password("securepassword"),
            role="user",
            is_active=True,
            is_superuser=False,
        )
    )

    result = await service.login(
        email=Email.from_raw("USER@example.com"),
        password="securepassword"
    )

    assert isinstance(result, TokenPair)
    assert result.access_token == f"access-token-for-{user.id}"
    assert result.refresh_token == f"refresh-token-for-{user.id}"
    assert result.token_type == "Bearer"


@pytest.mark.asyncio
async def test_login_fails_if_user_not_found():
    user_repo = InMemoryUserRepository()
    pwd_hasher = DummyPasswordHasher()
    token_service = FakeTokenService()
    service = AuthService(
        user_repo=user_repo,
        pwd_hasher=pwd_hasher,
        token_service=token_service
    )

    with pytest.raises(ValueError):
        await service.login(
            email=Email.from_raw("unknown@example.com"),
            password="any-password"
        )

@pytest.mark.asyncio
async def test_login_fails_if_password_invalid():
    user_repo = InMemoryUserRepository()
    pwd_hasher = DummyPasswordHasher()
    token_service = FakeTokenService()
    service = AuthService(
        user_repo=user_repo,
        pwd_hasher=pwd_hasher,
        token_service=token_service
    )

    # Create a user to login with
    await user_repo.create(
        User(
            id=None,
            email=Email.from_raw("user@example.com"),
            hashed_password=pwd_hasher.hash_password("secret"),
            role="user",
            is_active=True,
            is_superuser=False,
        )
    )

    with pytest.raises(ValueError):
        await service.login(
            email="user@example.com",
            password="wrong-password"
        )

@pytest.mark.asyncio
async def test_login_fails_if_user_inactive():
    user_repo = InMemoryUserRepository()
    pwd_hasher = DummyPasswordHasher()
    token_service = FakeTokenService()
    service = AuthService(
        user_repo=user_repo,
        pwd_hasher=pwd_hasher,
        token_service=token_service
    )

    user = User(
        id=None,
        email=Email.from_raw("inactive@example.com"),
        hashed_password=pwd_hasher.hash_password("secret"),
        role="user",
        is_active=False,
        is_superuser=False,
    )
    await user_repo.create(user)

    with pytest.raises(ValueError):
        await service.login(
            email=Email.from_raw("inactive@example.com"),
            password="secret"
        )


@pytest.mark.asyncio
async def test_login_fails_if_user_has_no_password():
    user_repo = InMemoryUserRepository()
    pwd_hasher = DummyPasswordHasher()
    token_service = FakeTokenService()
    service = AuthService(
        user_repo=user_repo,
        pwd_hasher=pwd_hasher,
        token_service=token_service
    )

    user = User(
        id=None,
        email=Email.from_raw("nopass@example.com"),
        hashed_password=None,
        role="user",
        is_active=True,
        is_superuser=False,
    )
    await user_repo.create(user)

    with pytest.raises(ValueError):
        await service.login(
            email="nopass@example.com",
            password="secret"
        )
