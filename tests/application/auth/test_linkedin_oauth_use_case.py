from typing import Optional, Mapping
from unittest.mock import AsyncMock
from uuid import UUID

import pytest

from app.application.auth.linkedin_oauth_use_case import LinkedInOAuthUseCase
from app.application.auth.ports import TokenService
from app.application.auth.use_cases import TokenPair
from app.domain.common.exceptions import UnauthorizedError
from app.domain.users.entities import User
from app.domain.users.value_objects import Email, LinkedInProfile
from tests.fakes.auth.fake_oauth_gateway import FakeOAuthGateway
from tests.fakes.users.in_memory_user_repo import InMemoryUserRepository


# ---------------------------------------------------------------------------
# Shared helpers / fakes
# ---------------------------------------------------------------------------

class FakeTokenService(TokenService):
    def create_access_token(self, subject: str, extra: Optional[Mapping] = None) -> str:
        return f"access-{subject}"

    def create_refresh_token(self, subject: str, extra: Optional[Mapping] = None) -> str:
        return f"refresh-{subject}"

    def decode_token(self, token: str) -> Mapping:
        return {}


def _make_profile(**kwargs) -> LinkedInProfile:
    defaults = dict(
        linkedin_id="li_abc123",
        email="alice@example.com",
        first_name="Alice",
        last_name="Smith",
        avatar_url="https://cdn.linkedin.com/alice.jpg",
    )
    return LinkedInProfile(**{**defaults, **kwargs})


def _make_use_case(
    profile: LinkedInProfile | None = None,
    raise_on_exchange: Exception | None = None,
    repo: InMemoryUserRepository | None = None,
) -> tuple[LinkedInOAuthUseCase, InMemoryUserRepository]:
    repo = repo or InMemoryUserRepository()
    gateway = FakeOAuthGateway(profile=profile, raise_on_exchange=raise_on_exchange)
    token_service = FakeTokenService()
    freemium = AsyncMock()
    freemium.execute = AsyncMock(return_value=None)

    use_case = LinkedInOAuthUseCase(
        oauth_gateway=gateway,
        user_repo=repo,
        token_service=token_service,
        freemium_use_case=freemium,
    )
    return use_case, repo


# ---------------------------------------------------------------------------
# Branch 1 — new user signup via LinkedIn
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_linkedin_oauth_creates_new_user():
    profile = _make_profile()
    use_case, repo = _make_use_case(profile=profile)

    result = await use_case.execute(code="auth_code", redirect_uri="https://app.jobai.io/cb")

    assert isinstance(result, TokenPair)
    assert result.token_type == "Bearer"

    # User was persisted
    user = await repo.get_by_email(Email.from_raw("alice@example.com"))
    assert user is not None
    assert user.linkedin_id == "li_abc123"
    assert user.first_name == "Alice"
    assert user.hashed_password is None


@pytest.mark.asyncio
async def test_linkedin_oauth_new_user_triggers_freemium():
    profile = _make_profile()
    repo = InMemoryUserRepository()
    gateway = FakeOAuthGateway(profile=profile)
    token_service = FakeTokenService()
    freemium = AsyncMock()
    freemium.execute = AsyncMock(return_value=None)

    use_case = LinkedInOAuthUseCase(
        oauth_gateway=gateway,
        user_repo=repo,
        token_service=token_service,
        freemium_use_case=freemium,
    )

    await use_case.execute(code="code", redirect_uri="https://cb")

    freemium.execute.assert_called_once()


# ---------------------------------------------------------------------------
# Branch 2 — returning user (linkedin_id already stored)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_linkedin_oauth_returns_existing_user_by_linkedin_id():
    repo = InMemoryUserRepository()
    existing = await repo.create(User(
        id=None,
        email=Email.from_raw("alice@example.com"),
        first_name="Alice",
        last_name="Smith",
        linkedin_id="li_abc123",
        avatar_url="https://old.jpg",
    ))

    profile = _make_profile()
    use_case, _ = _make_use_case(profile=profile, repo=repo)

    result = await use_case.execute(code="code", redirect_uri="https://cb")

    assert isinstance(result, TokenPair)
    # Token subject is the existing user's ID
    assert str(existing.id) in result.access_token

    # No duplicate created
    assert await repo.count() == 1


@pytest.mark.asyncio
async def test_linkedin_oauth_returning_user_does_not_trigger_freemium():
    repo = InMemoryUserRepository()
    await repo.create(User(
        id=None,
        email=Email.from_raw("alice@example.com"),
        linkedin_id="li_abc123",
    ))

    gateway = FakeOAuthGateway(profile=_make_profile())
    token_service = FakeTokenService()
    freemium = AsyncMock()
    freemium.execute = AsyncMock(return_value=None)

    use_case = LinkedInOAuthUseCase(
        oauth_gateway=gateway,
        user_repo=repo,
        token_service=token_service,
        freemium_use_case=freemium,
    )

    await use_case.execute(code="code", redirect_uri="https://cb")

    freemium.execute.assert_not_called()


# ---------------------------------------------------------------------------
# Branch 3 — email collision (existing password user connects via LinkedIn)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_linkedin_oauth_merges_linkedin_id_onto_existing_email_user():
    repo = InMemoryUserRepository()
    existing = await repo.create(User(
        id=None,
        email=Email.from_raw("alice@example.com"),
        hashed_password="hashed-secret",
        first_name="Alice",
        last_name="Smith",
    ))

    profile = _make_profile(avatar_url="https://new-avatar.jpg")
    use_case, _ = _make_use_case(profile=profile, repo=repo)

    result = await use_case.execute(code="code", redirect_uri="https://cb")

    assert isinstance(result, TokenPair)

    updated = await repo.get_by_email(Email.from_raw("alice@example.com"))
    assert updated.linkedin_id == "li_abc123"
    assert updated.avatar_url == "https://new-avatar.jpg"
    # Password must be preserved — not wiped
    assert updated.hashed_password == "hashed-secret"
    # No duplicate
    assert await repo.count() == 1


# ---------------------------------------------------------------------------
# Error case — invalid LinkedIn code
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_linkedin_oauth_raises_unauthorized_on_gateway_failure():
    use_case, _ = _make_use_case(raise_on_exchange=ValueError("Token expired"))

    with pytest.raises(UnauthorizedError) as exc_info:
        await use_case.execute(code="bad_code", redirect_uri="https://cb")

    assert exc_info.value.code == "linkedin_auth_failed"
