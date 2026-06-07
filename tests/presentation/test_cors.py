import importlib

from httpx import ASGITransport, AsyncClient
import pytest


@pytest.mark.asyncio
async def test_cors_allows_configured_origin_with_credentials(monkeypatch):
    """GIVEN the frontend origin is configured
    WHEN a preflight request comes from that origin
    THEN the API returns credentialed CORS headers for that exact origin
    """
    monkeypatch.setenv("CORS_ALLOW_ORIGINS", "https://app.jobai.test")
    monkeypatch.delenv("CORS_ALLOW_ORIGIN_REGEX", raising=False)

    import app.core.config as config_module
    import app.main as main_module

    importlib.reload(config_module)
    importlib.reload(main_module)

    transport = ASGITransport(app=main_module.create_app())
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.options(
            "/health",
            headers={
                "Origin": "https://app.jobai.test",
                "Access-Control-Request-Method": "GET",
            },
        )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "https://app.jobai.test"
    assert response.headers["access-control-allow-credentials"] == "true"


@pytest.mark.asyncio
async def test_cors_rejects_unconfigured_origin(monkeypatch):
    """GIVEN a strict frontend origin is configured
    WHEN a preflight request comes from another origin
    THEN the API does not grant CORS access
    """
    monkeypatch.setenv("CORS_ALLOW_ORIGINS", "https://app.jobai.test")
    monkeypatch.delenv("CORS_ALLOW_ORIGIN_REGEX", raising=False)

    import app.core.config as config_module
    import app.main as main_module

    importlib.reload(config_module)
    importlib.reload(main_module)

    transport = ASGITransport(app=main_module.create_app())
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.options(
            "/health",
            headers={
                "Origin": "https://evil.example",
                "Access-Control-Request-Method": "GET",
            },
        )

    assert response.status_code == 400
    assert "access-control-allow-origin" not in response.headers
    assert response.headers["access-control-allow-credentials"] == "true"


@pytest.mark.asyncio
async def test_cors_allows_matching_frontend_preview_origin_with_credentials(monkeypatch):
    preview_origin = (
        "https://jobai-frontend-hchgikv3c-"
        "rpsantosvix-gmailcoms-projects.vercel.app"
    )
    monkeypatch.setenv("CORS_ALLOW_ORIGINS", "https://jobai-app.vercel.app")
    monkeypatch.setenv(
        "CORS_ALLOW_ORIGIN_REGEX",
        (
            r"^https://jobai-frontend-[a-z0-9]+-"
            r"rpsantosvix-gmailcoms-projects\.vercel\.app$"
        ),
    )

    import app.core.config as config_module
    import app.main as main_module

    importlib.reload(config_module)
    importlib.reload(main_module)

    transport = ASGITransport(app=main_module.create_app())
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.options(
            "/api/v1/users/me",
            headers={
                "Origin": preview_origin,
                "Access-Control-Request-Method": "GET",
            },
        )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == preview_origin
    assert response.headers["access-control-allow-credentials"] == "true"


@pytest.mark.asyncio
async def test_cors_rejects_other_vercel_preview_project(monkeypatch):
    monkeypatch.setenv("CORS_ALLOW_ORIGINS", "https://jobai-app.vercel.app")
    monkeypatch.setenv(
        "CORS_ALLOW_ORIGIN_REGEX",
        (
            r"^https://jobai-frontend-[a-z0-9]+-"
            r"rpsantosvix-gmailcoms-projects\.vercel\.app$"
        ),
    )

    import app.core.config as config_module
    import app.main as main_module

    importlib.reload(config_module)
    importlib.reload(main_module)

    transport = ASGITransport(app=main_module.create_app())
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.options(
            "/api/v1/users/me",
            headers={
                "Origin": "https://unrelated-project-abc.vercel.app",
                "Access-Control-Request-Method": "GET",
            },
        )

    assert response.status_code == 400
    assert "access-control-allow-origin" not in response.headers
