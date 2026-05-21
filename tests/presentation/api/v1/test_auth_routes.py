from datetime import UTC, datetime

import pytest

from app.application.auth.use_cases import RefreshTokenClaims
from app.infrastructure.persistence.repositories.refresh_token_sqlalchemy import (
    SQLAlchemyRefreshTokenRepository,
)

_VALID_PASSWORD = "SecurePass1!"
_VALID_PAYLOAD = {
    "email": "candidate@example.com",
    "password": _VALID_PASSWORD,
    "first_name": "Thomas",
    "last_name": "Dupont",
}


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


# ---------------------------------------------------------------------------
# POST /auth/register
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_register_returns_201_with_access_token_and_httponly_cookie(client):
    """201 + body contient access_token + cookie refresh_token httpOnly Secure SameSite=Lax."""
    response = await client.post("/api/v1/auth/register", json=_VALID_PAYLOAD)

    assert response.status_code == 201
    body = response.json()
    assert "access_token" in body
    assert body.get("token_type") == "Bearer"
    assert "user" in body
    assert body["user"]["email"] == "candidate@example.com"
    set_cookie = response.headers["set-cookie"]
    assert "refresh_token=" in set_cookie
    assert "HttpOnly" in set_cookie
    assert "Secure" in set_cookie
    assert "SameSite=lax" in set_cookie.lower()
    assert "Max-Age=604800" in set_cookie


@pytest.mark.asyncio
async def test_register_response_body_does_not_contain_refresh_token(client):
    """Le refresh_token NE DOIT PAS apparaître dans le body — cookie uniquement."""
    response = await client.post("/api/v1/auth/register", json=_VALID_PAYLOAD | {"email": "notoken@example.com"})

    assert response.status_code == 201
    body = response.json()
    assert "refresh_token" not in body


@pytest.mark.asyncio
async def test_register_returns_409_on_duplicate_email(client, create_user_in_db):
    """409 si l'email est déjà enregistré."""
    await create_user_in_db("taken@example.com")

    response = await client.post(
        "/api/v1/auth/register",
        json=_VALID_PAYLOAD | {"email": "taken@example.com"},
    )

    assert response.status_code == 409
    assert response.json()["code"] == "user_already_exists"


@pytest.mark.asyncio
async def test_register_returns_422_on_weak_password(client):
    """422 si le mot de passe ne respecte pas D4 (≥12, maj, chiffre, spécial)."""
    weak_passwords = [
        "short1A!",          # < 12 chars
        "nouppercase1!aaa",  # no uppercase
        "NoDigitHere!!!a",   # no digit
        "NoSpecialChar1a",   # no special char
    ]
    for pwd in weak_passwords:
        response = await client.post(
            "/api/v1/auth/register",
            json=_VALID_PAYLOAD | {"email": f"weak{pwd[:4]}@example.com", "password": pwd},
        )
        assert response.status_code == 422, f"Expected 422 for password={pwd!r}, got {response.status_code}"


@pytest.mark.asyncio
async def test_register_refresh_cookie_is_usable_for_subsequent_refresh(client):
    """Le cookie refresh_token émis au register permet un appel /auth/refresh réussi."""
    register_response = await client.post(
        "/api/v1/auth/register",
        json=_VALID_PAYLOAD | {"email": "refreshable@example.com"},
    )
    assert register_response.status_code == 201

    refresh_response = await client.post("/api/v1/auth/refresh")

    assert refresh_response.status_code == 200
    body = refresh_response.json()
    assert "access_token" in body


@pytest.mark.asyncio
async def test_register_returns_422_on_invalid_email(client):
    """422 si l'email n'est pas un format valide."""
    response = await client.post(
        "/api/v1/auth/register",
        json=_VALID_PAYLOAD | {"email": "notanemail"},
    )

    assert response.status_code == 422
    assert response.json()["code"] == "validation_error"


@pytest.mark.asyncio
async def test_register_returns_422_when_first_name_is_missing(client):
    """422 si first_name est absent du body."""
    payload = {k: v for k, v in _VALID_PAYLOAD.items() if k != "first_name"}
    payload["email"] = "nofirst@example.com"

    response = await client.post("/api/v1/auth/register", json=payload)

    assert response.status_code == 422
    assert response.json()["code"] == "validation_error"


@pytest.mark.asyncio
async def test_register_returns_422_when_last_name_is_missing(client):
    """422 si last_name est absent du body."""
    payload = {k: v for k, v in _VALID_PAYLOAD.items() if k != "last_name"}
    payload["email"] = "nolast@example.com"

    response = await client.post("/api/v1/auth/register", json=payload)

    assert response.status_code == 422
    assert response.json()["code"] == "validation_error"
