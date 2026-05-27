"""
Tests for LinkedInOAuthUseCase (authorization URL + account linking).
Callback OAuth flow tests live in test_linkedin_callback_use_case.py.
"""
from uuid import uuid4

import pytest
from unittest.mock import AsyncMock

from app.application.auth.linkedin_oauth_use_case import LinkedInOAuthUseCase
from app.domain.common.exceptions import ConflictError, UnauthorizedError
from app.domain.users.entities import Candidate
from app.domain.users.value_objects import Email, LinkedInProfile
from tests.fakes.auth.fake_oauth_gateway import FakeOAuthGateway
from tests.fakes.users.in_memory_user_repo import InMemoryUserRepository


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
    use_case = LinkedInOAuthUseCase(oauth_gateway=gateway, user_repo=repo)
    return use_case, repo


# ---------------------------------------------------------------------------
# build_authorization_url
# ---------------------------------------------------------------------------

def test_build_authorization_url_delegates_to_gateway():
    use_case, _ = _make_use_case(profile=_make_profile())
    url = use_case.build_authorization_url(
        redirect_uri="https://app.jobai.io/cb", state="csrf-token-xyz"
    )
    assert "linkedin.com" in url
    assert "csrf-token-xyz" in url


# ---------------------------------------------------------------------------
# link_to_existing_user — attach LinkedIn to an authenticated Candidate
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_link_to_existing_user_attaches_linkedin_id():
    repo = InMemoryUserRepository()
    existing = await repo.create(Candidate(
        id=uuid4(),
        email=Email.from_raw("alice@example.com"),
        hashed_password="hashed-secret",
    ))

    profile = _make_profile(avatar_url="https://new-avatar.jpg")
    use_case, _ = _make_use_case(profile=profile, repo=repo)

    await use_case.link_to_existing_user(
        current_user_id=existing.id,
        code="code",
        redirect_uri="https://cb",
    )

    updated = await repo.get_by_email(Email.from_raw("alice@example.com"))
    assert updated.linkedin_id == "li_abc123"
    assert updated.avatar_url == "https://new-avatar.jpg"
    assert updated.hashed_password == "hashed-secret"
    assert await repo.count() == 1


@pytest.mark.asyncio
async def test_link_to_existing_user_raises_conflict_if_linkedin_id_taken_by_other():
    repo = InMemoryUserRepository()
    await repo.create(Candidate(
        id=uuid4(),
        email=Email.from_raw("other@example.com"),
        linkedin_id="li_abc123",
    ))
    target = await repo.create(Candidate(
        id=uuid4(),
        email=Email.from_raw("alice@example.com"),
        hashed_password="hashed-secret",
    ))

    profile = _make_profile(linkedin_id="li_abc123")
    use_case, _ = _make_use_case(profile=profile, repo=repo)

    with pytest.raises(ConflictError) as exc_info:
        await use_case.link_to_existing_user(
            current_user_id=target.id,
            code="code",
            redirect_uri="https://cb",
        )

    assert exc_info.value.code == "linkedin_already_linked"


@pytest.mark.asyncio
async def test_link_to_existing_user_raises_unauthorized_on_bad_code():
    repo = InMemoryUserRepository()
    user = await repo.create(Candidate(id=None, email=Email.from_raw("alice@example.com")))

    use_case, _ = _make_use_case(raise_on_exchange=ValueError("expired"), repo=repo)

    with pytest.raises(UnauthorizedError) as exc_info:
        await use_case.link_to_existing_user(
            current_user_id=user.id,
            code="bad",
            redirect_uri="https://cb",
        )

    assert exc_info.value.code == "linkedin_auth_failed"
