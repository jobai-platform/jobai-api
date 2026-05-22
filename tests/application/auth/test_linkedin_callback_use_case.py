"""
Tests TDD pour LinkedInCallbackUseCase
Bounded Context : Users / Auth
Layer : application
"""
from typing import Optional, Mapping
from unittest.mock import AsyncMock

import pytest

from app.application.auth.linkedin_callback_use_case import LinkedInCallbackUseCase
from app.application.auth.ports import TokenService
from app.application.auth.use_cases import LinkedInAuthResult
from app.domain.common.exceptions import ConflictError, UnauthorizedError
from app.domain.users.entities import Candidate
from app.domain.users.value_objects import Email, LinkedInProfile
from tests.fakes.auth.fake_oauth_gateway import FakeOAuthGateway
from tests.fakes.users.in_memory_user_repo import InMemoryUserRepository


class FakeTokenService(TokenService):
    def create_access_token(self, subject: str, extra: Optional[Mapping] = None) -> str:
        return f"access-{subject}"

    def create_refresh_token(self, subject: str, extra: Optional[Mapping] = None) -> str:
        return f"refresh-{subject}"

    def decode_token(self, token: str) -> Mapping:
        return {}

    def validate_refresh_token(self, token: str) -> str:
        raise NotImplementedError


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
) -> tuple[LinkedInCallbackUseCase, InMemoryUserRepository]:
    repo = repo or InMemoryUserRepository()
    gateway = FakeOAuthGateway(profile=profile, raise_on_exchange=raise_on_exchange)
    freemium = AsyncMock()
    freemium.execute = AsyncMock(return_value=None)

    use_case = LinkedInCallbackUseCase(
        oauth_gateway=gateway,
        user_repo=repo,
        token_service=FakeTokenService(),
        freemium_use_case=freemium,
    )
    return use_case, repo


# ---------------------------------------------------------------------------
# Happy path — new Candidate signup via LinkedIn
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_callback_creates_new_candidate_and_returns_is_new_user_true():
    profile = _make_profile()
    use_case, repo = _make_use_case(profile=profile)

    result = await use_case.execute(code="auth_code", redirect_uri="https://app.jobai.io/cb")

    assert isinstance(result, LinkedInAuthResult)
    assert result.is_new_user is True
    assert result.token_type == "Bearer"

    user = await repo.get_by_email(Email.from_raw("alice@example.com"))
    assert user is not None
    assert user.linkedin_id == "li_abc123"
    assert user.hashed_password is None


@pytest.mark.asyncio
async def test_callback_new_candidate_triggers_freemium():
    profile = _make_profile()
    repo = InMemoryUserRepository()
    freemium = AsyncMock()
    freemium.execute = AsyncMock(return_value=None)

    use_case = LinkedInCallbackUseCase(
        oauth_gateway=FakeOAuthGateway(profile=profile),
        user_repo=repo,
        token_service=FakeTokenService(),
        freemium_use_case=freemium,
    )

    await use_case.execute(code="code", redirect_uri="https://cb")

    freemium.execute.assert_called_once()


# ---------------------------------------------------------------------------
# Happy path — returning Candidate (linkedin_id already stored)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_callback_returns_existing_candidate_and_is_new_user_false():
    repo = InMemoryUserRepository()
    existing = await repo.create(Candidate(
        id=None,
        email=Email.from_raw("alice@example.com"),
        first_name="Alice",
        last_name="Smith",
        linkedin_id="li_abc123",
        avatar_url="https://old.jpg",
    ))

    use_case, _ = _make_use_case(profile=_make_profile(), repo=repo)

    result = await use_case.execute(code="code", redirect_uri="https://cb")

    assert isinstance(result, LinkedInAuthResult)
    assert result.is_new_user is False
    assert str(existing.id) in result.access_token
    assert await repo.count() == 1


@pytest.mark.asyncio
async def test_callback_returning_candidate_does_not_trigger_freemium():
    repo = InMemoryUserRepository()
    await repo.create(Candidate(
        id=None,
        email=Email.from_raw("alice@example.com"),
        linkedin_id="li_abc123",
    ))

    freemium = AsyncMock()
    freemium.execute = AsyncMock(return_value=None)

    use_case = LinkedInCallbackUseCase(
        oauth_gateway=FakeOAuthGateway(profile=_make_profile()),
        user_repo=repo,
        token_service=FakeTokenService(),
        freemium_use_case=freemium,
    )

    await use_case.execute(code="code", redirect_uri="https://cb")

    freemium.execute.assert_not_called()


# ---------------------------------------------------------------------------
# Error — email collision (D9 scenario)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_callback_raises_conflict_when_email_already_registered():
    """
    D9: LinkedIn signup with an email already registered via password.
    Prevents duplicate accounts — Candidate must log in and link from settings.
    """
    repo = InMemoryUserRepository()
    await repo.create(Candidate(
        id=None,
        email=Email.from_raw("alice@example.com"),
        hashed_password="hashed-secret",
    ))

    use_case, _ = _make_use_case(profile=_make_profile(), repo=repo)

    with pytest.raises(ConflictError) as exc_info:
        await use_case.execute(code="code", redirect_uri="https://cb")

    assert exc_info.value.code == "email_already_used"
    assert await repo.count() == 1  # no duplicate created


# ---------------------------------------------------------------------------
# Error — invalid LinkedIn code
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_callback_raises_unauthorized_on_gateway_failure():
    use_case, _ = _make_use_case(raise_on_exchange=ValueError("Token expired"))

    with pytest.raises(UnauthorizedError) as exc_info:
        await use_case.execute(code="bad_code", redirect_uri="https://cb")

    assert exc_info.value.code == "linkedin_auth_failed"
