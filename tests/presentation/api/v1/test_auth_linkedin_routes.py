import pytest
from unittest.mock import AsyncMock, MagicMock

from app.application.auth.linkedin_oauth_use_case import LinkedInOAuthUseCase
from app.application.auth.use_cases import TokenPair
from app.core.dependency import get_linkedin_oauth_use_case
from app.domain.common.exceptions import UnauthorizedError


def _make_fake_use_case(
    token_pair: TokenPair | None = None,
    raise_exc: Exception | None = None,
) -> MagicMock:
    fake = MagicMock(spec=LinkedInOAuthUseCase)
    if raise_exc:
        fake.execute = AsyncMock(side_effect=raise_exc)
    else:
        pair = token_pair or TokenPair(
            access_token="access-abc",
            refresh_token="refresh-abc",
            token_type="Bearer",
        )
        fake.execute = AsyncMock(return_value=pair)

    # build_authorization_url must return a real string (Pydantic validates it)
    fake.build_authorization_url = MagicMock(
        return_value="https://www.linkedin.com/oauth/v2/authorization?client_id=test&redirect_uri=https://cb&state=xyz"
    )
    return fake


# ---------------------------------------------------------------------------
# GET /api/v1/auth/linkedin — authorization URL
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_linkedin_auth_url_returns_200(client):
    fake = _make_fake_use_case()

    from app.main import app
    app.dependency_overrides[get_linkedin_oauth_use_case] = lambda: fake

    response = await client.get(
        "/api/v1/auth/linkedin",
        params={"redirect_uri": "https://app.jobai.io/auth/callback"},
    )

    app.dependency_overrides.pop(get_linkedin_oauth_use_case, None)

    assert response.status_code == 200
    data = response.json()
    assert "authorization_url" in data
    assert "linkedin.com" in data["authorization_url"]


# ---------------------------------------------------------------------------
# POST /api/v1/auth/linkedin/callback — happy path
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_linkedin_callback_new_user_returns_200(client):
    fake = _make_fake_use_case()

    from app.main import app
    app.dependency_overrides[get_linkedin_oauth_use_case] = lambda: fake

    response = await client.post(
        "/api/v1/auth/linkedin/callback",
        json={"code": "valid_code", "redirect_uri": "https://app.jobai.io/auth/callback"},
    )

    app.dependency_overrides.pop(get_linkedin_oauth_use_case, None)

    assert response.status_code == 200
    data = response.json()
    assert data["access_token"] == "access-abc"
    assert data["refresh_token"] == "refresh-abc"
    assert data["token_type"] == "Bearer"


# ---------------------------------------------------------------------------
# POST /api/v1/auth/linkedin/callback — invalid code → 401
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_linkedin_callback_returns_401_on_bad_code(client):
    fake = _make_fake_use_case(
        raise_exc=UnauthorizedError(
            code="linkedin_auth_failed",
            details="LinkedIn authentication failed.",
        )
    )

    from app.main import app
    app.dependency_overrides[get_linkedin_oauth_use_case] = lambda: fake

    response = await client.post(
        "/api/v1/auth/linkedin/callback",
        json={"code": "bad_code", "redirect_uri": "https://app.jobai.io/auth/callback"},
    )

    app.dependency_overrides.pop(get_linkedin_oauth_use_case, None)

    assert response.status_code == 401


# ---------------------------------------------------------------------------
# POST /api/v1/auth/linkedin/callback — missing fields → 422
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_linkedin_callback_returns_422_on_missing_fields(client):
    response = await client.post(
        "/api/v1/auth/linkedin/callback",
        json={"code": "only_code"},  # redirect_uri missing
    )
    assert response.status_code == 422
