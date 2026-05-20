from datetime import UTC, datetime

import pytest

from app.application.auth.use_cases import RefreshTokenClaims
from app.infrastructure.persistence.repositories.refresh_token_sqlalchemy import (
    SQLAlchemyRefreshTokenRepository,
)


def _expires_at_from_claim(value: object) -> datetime:
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=UTC)
    if isinstance(value, int | float):
        return datetime.fromtimestamp(value, tz=UTC)
    raise TypeError("Unsupported exp claim")


async def _persist_refresh_token(db_session, jwt_service, user_id, token: str) -> RefreshTokenClaims:
    claims = jwt_service.decode_token(token)
    refresh_claims = RefreshTokenClaims(
        subject=user_id,
        jti=str(claims["jti"]),
        expires_at=_expires_at_from_claim(claims["exp"]),
    )
    repo = SQLAlchemyRefreshTokenRepository(db_session)
    await repo.persist(jti=refresh_claims.jti, user_id=refresh_claims.subject, expires_at=refresh_claims.expires_at)
    return refresh_claims


@pytest.mark.asyncio
async def test_logout_returns_204_and_expires_refresh_cookie(client, db_session, create_user_in_db, jwt_service):
    user = await create_user_in_db("logout@example.com")
    refresh_token = jwt_service.create_refresh_token(subject=str(user.id), extra={"role": user.role, "email": user.email})
    await _persist_refresh_token(db_session, jwt_service, user.id, refresh_token)
    client.cookies.set("refresh_token", refresh_token)

    response = await client.post("/api/v1/auth/logout")

    assert response.status_code == 204
    set_cookie = response.headers["set-cookie"]
    assert "refresh_token=" in set_cookie
    assert "Max-Age=0" in set_cookie


@pytest.mark.asyncio
async def test_refresh_cookie_replay_after_logout_returns_401(client, db_session, create_user_in_db, jwt_service):
    user = await create_user_in_db("replay@example.com")
    refresh_token = jwt_service.create_refresh_token(subject=str(user.id), extra={"role": user.role, "email": user.email})
    await _persist_refresh_token(db_session, jwt_service, user.id, refresh_token)
    client.cookies.set("refresh_token", refresh_token)

    logout_response = await client.post("/api/v1/auth/logout")
    assert logout_response.status_code == 204

    client.cookies.set("refresh_token", refresh_token)
    replay_response = await client.post("/api/v1/auth/refresh")

    assert replay_response.status_code == 401
    assert replay_response.json()["code"] == "invalid_authentication"


@pytest.mark.asyncio
async def test_logout_without_refresh_cookie_returns_204(client):
    response = await client.post("/api/v1/auth/logout")

    assert response.status_code == 204
    assert "Max-Age=0" in response.headers["set-cookie"]


@pytest.mark.asyncio
async def test_refresh_returns_200_with_new_cookie_and_access_token(
    client, db_session, create_user_in_db, jwt_service
):
    user = await create_user_in_db("refresh@example.com")
    old_token = jwt_service.create_refresh_token(
        subject=str(user.id), extra={"role": user.role, "email": user.email}
    )
    await _persist_refresh_token(db_session, jwt_service, user.id, old_token)
    client.cookies.set("refresh_token", old_token)

    response = await client.post("/api/v1/auth/refresh")

    assert response.status_code == 200
    body = response.json()
    assert "access_token" in body
    assert body.get("token_type") == "Bearer"
    set_cookie = response.headers["set-cookie"]
    assert "refresh_token=" in set_cookie
    assert "HttpOnly" in set_cookie
    assert "Max-Age=604800" in set_cookie
    new_token = response.cookies.get("refresh_token")
    assert new_token is not None
    assert new_token != old_token


@pytest.mark.asyncio
async def test_refresh_without_cookie_returns_401(client):
    response = await client.post("/api/v1/auth/refresh")

    assert response.status_code == 401
    assert response.headers.get("www-authenticate") == "Bearer"
