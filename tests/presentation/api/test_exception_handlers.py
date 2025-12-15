import pytest
from fastapi import FastAPI
from httpx import AsyncClient, ASGITransport

from app.domain.common.exceptions import (
    NotFoundError,
    ConflictError,
    UnauthorizedError,
    ForbiddenError,
    BadRequestError,
    ValidationError,
)
from app.presentation.api.exception_handlers import setup_exception_handlers


@pytest.mark.asyncio
async def test_maps_not_found_error_to_404_exception():
    app = FastAPI()
    setup_exception_handlers(app)

    @app.get("/test-not-found")
    async def test_not_found():
        raise NotFoundError("user_not_found", details="user does not exist")

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/test-not-found")

    assert response.status_code == 404
    assert response.json() == {
        "detail": "user does not exist",
        "code": "user_not_found",
    }


@pytest.mark.asyncio
async def test_maps_conflict_error_to_409_exception():
    app = FastAPI()
    setup_exception_handlers(app)

    @app.post("/test-conflict")
    async def test_conflict():
        raise ConflictError("user_already_exists", details="Email already exists")

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/test-conflict")

    assert response.status_code == 409
    assert response.json() == {
        "detail": "Email already exists",
        "code": "user_already_exists",
    }


@pytest.mark.asyncio
async def test_maps_unauthorized_error_to_401_exception():
    app = FastAPI()
    setup_exception_handlers(app)

    @app.get("/test-unauthorized")
    async def test_unauthorized():
        raise UnauthorizedError("invalid_credentials", details="Invalid credentials")

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/test-unauthorized")

    assert response.status_code == 401
    assert response.json() == {
        "detail": "Invalid credentials",
        "code": "invalid_credentials",
    }


@pytest.mark.asyncio
async def test_maps_forbidden_error_to_403_exception():
    app = FastAPI()
    setup_exception_handlers(app)

    @app.get("/test-forbidden")
    async def test_forbidden():
        raise ForbiddenError("access_denied", details="Access denied")

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/test-forbidden")

    assert response.status_code == 403
    assert response.json() == {
        "detail": "Access denied",
        "code": "access_denied",
    }


@pytest.mark.asyncio
async def test_maps_bad_request_error_to_400_exception():
    app = FastAPI()
    setup_exception_handlers(app)

    @app.get("/test-bad-request")
    async def test_bad_request():
        raise BadRequestError("invalid_request", details="Invalid request parameters")

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/test-bad-request")

    assert response.status_code == 400
    assert response.json() == {
        "detail": "Invalid request parameters",
        "code": "invalid_request",
    }


@pytest.mark.asyncio
async def test_maps_validation_error_to_422_exception():
    app = FastAPI()
    setup_exception_handlers(app)

    @app.get("/test-validation-error")
    async def test_validation_error():
        raise ValidationError("validation_failed", details="Data validation failed")

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/test-validation-error")

    assert response.status_code == 422
    assert response.json() == {
        "detail": "Data validation failed",
        "code": "validation_failed",
    }
