import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.presentation.api.exception_handlers import setup_exception_handlers
from app.presentation.api.v1.schemas.users import UserCreate


@pytest.mark.asyncio
async def test_request_validation_error_returns_422_with_code_and_errors():
    app = FastAPI()
    setup_exception_handlers(app)

    @app.post("/users")
    async def create_user(payload: UserCreate):
        return {"ok": True}

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        res = await client.post(
            "/users",
            json={
                "email": "not-an-email",
                "password": "short",  # min_length=8 => validation error too
            },
        )

    assert res.status_code == 422
    body = res.json()
    assert body["code"] == "validation_error"
    assert body["detail"] == "Request validation failed"
    assert "errors" in body
    assert isinstance(body["errors"], list)

    # At least one error should reference the email field
    assert any(err.get("loc") == ["body", "email"] for err in body["errors"])


@pytest.mark.asyncio
async def test_request_validation_error_missing_required_field_email():
    app = FastAPI()
    setup_exception_handlers(app)

    @app.post("/users")
    async def create_user(payload: UserCreate):
        return {"ok": True}

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        res = await client.post(
            "/users",
            json={
                "password": "securepassword",
            },
        )

    assert res.status_code == 422
    body = res.json()
    assert body["code"] == "validation_error"
    assert body["detail"] == "Request validation failed"
    assert isinstance(body.get("errors"), list)
    assert any(err.get("loc") == ["body", "email"] for err in body["errors"])
