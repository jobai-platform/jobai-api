"""
Tests TDD pour LinkedIn OAuth routes
Bounded Context : Users / Auth
Layer : presentation
"""
import importlib
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.application.auth.linkedin_callback_use_case import LinkedInCallbackUseCase
from app.application.auth.linkedin_oauth_use_case import LinkedInOAuthUseCase
from app.application.auth.use_cases import LinkedInAuthResult
from app.core.dependency import get_linkedin_callback_use_case, get_linkedin_oauth_use_case
from app.domain.common.exceptions import ConflictError, UnauthorizedError


def _make_fake_callback_use_case(
    result: "LinkedInAuthResult | None" = None,
    raise_exc: Exception | None = None,
) -> MagicMock:
    fake = MagicMock(spec=LinkedInCallbackUseCase)
    if raise_exc:
        fake.execute = AsyncMock(side_effect=raise_exc)
    else:
        auth_result = result or LinkedInAuthResult(
            access_token="access-abc",
            refresh_token="refresh-abc",
            token_type="Bearer",
            is_new_user=True,
        )
        fake.execute = AsyncMock(return_value=auth_result)
    return fake


def _make_fake_oauth_use_case() -> MagicMock:
    fake = MagicMock(spec=LinkedInOAuthUseCase)
    fake.build_authorization_url = MagicMock(
        return_value=(
            "https://www.linkedin.com/oauth/v2/authorization"
            "?client_id=test&redirect_uri=https://cb&state=xyz"
        )
    )
    return fake


# ---------------------------------------------------------------------------
# GET /api/v1/auth/linkedin — authorization URL + state
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_linkedin_auth_url_returns_200_with_state(client):
    fake = _make_fake_oauth_use_case()

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
    assert "state" in data
    assert data["state"]  # non-empty — frontend stores for CSRF check


@pytest.mark.asyncio
async def test_linkedin_callback_get_uses_public_api_base_url(monkeypatch, client):
    monkeypatch.setenv(
        "LINKEDIN_REDIRECT_URI",
        "https://api.preview.test/api/v1/auth/linkedin/callback",
    )

    import app.core.config as config_module
    import app.presentation.api.v1.auth_routes as auth_routes_module

    importlib.reload(config_module)
    importlib.reload(auth_routes_module)

    response = await client.get(
        "/api/v1/auth/linkedin/callback",
        params={"code": "abc123", "state": "csrf-token-xyz"},
    )

    assert response.status_code == 200
    assert response.json()["redirect_uri"] == "https://api.preview.test/api/v1/auth/linkedin/callback"


# ---------------------------------------------------------------------------
# POST /api/v1/auth/linkedin/callback — new user (is_new_user=True)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_linkedin_callback_new_user_returns_200_with_cookie_and_is_new_user(client):
    fake = _make_fake_callback_use_case(
        result=LinkedInAuthResult(
            access_token="access-abc",
            refresh_token="refresh-abc",
            token_type="Bearer",
            is_new_user=True,
        )
    )

    from app.main import app
    app.dependency_overrides[get_linkedin_callback_use_case] = lambda: fake

    response = await client.post(
        "/api/v1/auth/linkedin/callback",
        json={"code": "valid_code", "redirect_uri": "https://app.jobai.io/auth/callback", "state": "csrf-token-xyz"},
    )

    app.dependency_overrides.pop(get_linkedin_callback_use_case, None)

    assert response.status_code == 200
    data = response.json()
    assert data["access_token"] == "access-abc"
    assert data["is_new_user"] is True
    assert "refresh_token" not in data  # refresh_token is in the cookie, not the body
    assert "refresh_token" in response.cookies  # httpOnly cookie set


# ---------------------------------------------------------------------------
# POST /api/v1/auth/linkedin/callback — returning user (is_new_user=False)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_linkedin_callback_existing_user_returns_200_with_is_new_user_false(client):
    fake = _make_fake_callback_use_case(
        result=LinkedInAuthResult(
            access_token="access-xyz",
            refresh_token="refresh-xyz",
            token_type="Bearer",
            is_new_user=False,
        )
    )

    from app.main import app
    app.dependency_overrides[get_linkedin_callback_use_case] = lambda: fake

    response = await client.post(
        "/api/v1/auth/linkedin/callback",
        json={"code": "valid_code", "redirect_uri": "https://app.jobai.io/auth/callback", "state": "csrf-token-xyz"},
    )

    app.dependency_overrides.pop(get_linkedin_callback_use_case, None)

    assert response.status_code == 200
    data = response.json()
    assert data["access_token"] == "access-xyz"
    assert data["is_new_user"] is False
    assert "refresh_token" not in data
    assert "refresh_token" in response.cookies


# ---------------------------------------------------------------------------
# POST /api/v1/auth/linkedin/callback — email collision → 409
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_linkedin_callback_returns_409_on_email_conflict(client):
    fake = _make_fake_callback_use_case(
        raise_exc=ConflictError(
            code="email_already_used",
            details="An account with this email already exists. Please log in with your password.",
        )
    )

    from app.main import app
    app.dependency_overrides[get_linkedin_callback_use_case] = lambda: fake

    response = await client.post(
        "/api/v1/auth/linkedin/callback",
        json={"code": "conflict_code", "redirect_uri": "https://app.jobai.io/auth/callback", "state": "csrf-token-xyz"},
    )

    app.dependency_overrides.pop(get_linkedin_callback_use_case, None)

    assert response.status_code == 409
    data = response.json()
    assert data["code"] == "email_already_used"


# ---------------------------------------------------------------------------
# POST /api/v1/auth/linkedin/callback — invalid code → 401
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_linkedin_callback_returns_401_on_bad_code(client):
    fake = _make_fake_callback_use_case(
        raise_exc=UnauthorizedError(
            code="linkedin_auth_failed",
            details="LinkedIn authentication failed.",
        )
    )

    from app.main import app
    app.dependency_overrides[get_linkedin_callback_use_case] = lambda: fake

    response = await client.post(
        "/api/v1/auth/linkedin/callback",
        json={"code": "bad_code", "redirect_uri": "https://app.jobai.io/auth/callback", "state": "csrf-token-xyz"},
    )

    app.dependency_overrides.pop(get_linkedin_callback_use_case, None)

    assert response.status_code == 401


# ---------------------------------------------------------------------------
# POST /api/v1/auth/linkedin/callback — missing fields → 422
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_linkedin_callback_returns_422_on_missing_fields(client):
    response = await client.post(
        "/api/v1/auth/linkedin/callback",
        json={"code": "only_code"},  # redirect_uri and state missing
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_linkedin_callback_returns_422_on_empty_state(client):
    response = await client.post(
        "/api/v1/auth/linkedin/callback",
        json={"code": "c", "redirect_uri": "https://app.jobai.io/cb", "state": ""},
    )
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# POST /api/v1/auth/linkedin/callback — 409 body contains actionable detail
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_linkedin_callback_409_body_has_actionable_detail(client):
    fake = _make_fake_callback_use_case(
        raise_exc=ConflictError(
            code="email_already_used",
            details="An account with this email already exists. Please log in with your password.",
        )
    )

    from app.main import app
    app.dependency_overrides[get_linkedin_callback_use_case] = lambda: fake

    response = await client.post(
        "/api/v1/auth/linkedin/callback",
        json={"code": "c", "redirect_uri": "https://app.jobai.io/cb", "state": "s"},
    )

    app.dependency_overrides.pop(get_linkedin_callback_use_case, None)

    assert response.status_code == 409
    data = response.json()
    assert data["code"] == "email_already_used"
    assert "password" in data["detail"]
    assert "settings" not in data["detail"]  # guard: dead link must not reappear


# ---------------------------------------------------------------------------
# POST /api/v1/auth/linkedin/callback — cookie security attributes
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_linkedin_callback_refresh_cookie_is_httponly(client):
    fake = _make_fake_callback_use_case()

    from app.main import app
    app.dependency_overrides[get_linkedin_callback_use_case] = lambda: fake

    response = await client.post(
        "/api/v1/auth/linkedin/callback",
        json={"code": "c", "redirect_uri": "https://app.jobai.io/cb", "state": "s"},
    )

    app.dependency_overrides.pop(get_linkedin_callback_use_case, None)

    set_cookie_header = response.headers.get("set-cookie", "")
    assert "HttpOnly" in set_cookie_header
    assert "SameSite=lax" in set_cookie_header
