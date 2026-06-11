from datetime import UTC, datetime
import hashlib
from uuid import UUID, uuid4

import pytest
from sqlalchemy import select

from app.domain.users.refresh_token import RefreshToken
from app.infrastructure.persistence.models.user import UserModel
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


async def _persist_refresh_token(db_session, jwt_service, user_id: UUID, token: str) -> None:
    claims = jwt_service.decode_token(token)
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    repo = SQLAlchemyRefreshTokenRepository(db_session)
    await repo.save(RefreshToken(
        id=uuid4(),
        token_hash=token_hash,
        user_id=user_id,
        expires_at=_expires_at_from_claim(claims["exp"]),
    ))


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
# POST /auth/token (Login)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_login_returns_refresh_token_in_cookie_and_not_in_body(client, create_user_in_db):
    """
    Le système DOIT retourner le refresh_token dans un cookie httpOnly
    et NE PAS l'inclure dans le corps de la réponse JSON.
    """
    # Arrange
    user = await create_user_in_db("login-test@example.com")
    payload = {
        "username": user.email,
        "password": _VALID_PASSWORD,
    }

    # Act
    response = await client.post(
        "/api/v1/auth/token",
        data=payload,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )

    # Assert
    assert response.status_code == 200

    # 1. Vérification du corps JSON
    body = response.json()
    assert "access_token" in body
    assert body.get("token_type") == "Bearer"
    assert "refresh_token" not in body, "Le refresh_token ne doit plus être présent dans le corps JSON"

    # 2. Vérification du cookie
    cookie = response.cookies.get("refresh_token")
    assert cookie is not None, "Le refresh_token doit être présent dans les cookies"

    # Vérification des attributs du cookie via le header Set-Cookie
    set_cookie_header = response.headers.get("set-cookie", "")
    assert "HttpOnly" in set_cookie_header
    assert "Secure" in set_cookie_header
    assert "samesite=lax" in set_cookie_header.lower()
    assert "Max-Age=604800" in set_cookie_header


@pytest.mark.asyncio
async def test_login_returns_401_with_invalid_credentials(client):
    """Le système DOIT retourner une erreur 401 quand les identifiants sont invalides."""
    # Arrange
    payload = {
        "username": "wrong@example.com",
        "password": "WrongPassword123!",
    }

    # Act
    response = await client.post(
        "/api/v1/auth/token",
        data=payload,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )

    # Assert
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid email or password"


@pytest.mark.asyncio
async def test_login_accepts_form_urlencoded(client, create_user_in_db):
    """L'endpoint DOIT accepter le format application/x-www-form-urlencoded (standard OAuth2)."""
    # Arrange
    user = await create_user_in_db("form-test@example.com")
    payload = {
        "username": user.email,
        "password": _VALID_PASSWORD,
    }

    # Act
    response = await client.post(
        "/api/v1/auth/token",
        data=payload,
    )

    # Assert
    # On vérifie que ce n'est pas une erreur de validation 422
    assert response.status_code != 422
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_register_returns_201_with_access_token_and_httponly_cookie(client):
    """201 + body contient access_token + cookie refresh_token httpOnly Secure SameSite=Lax."""
    response = await client.post("/api/v1/auth/register", json=_VALID_PAYLOAD)

    assert response.status_code == 201
    body = response.json()
    assert "access_token" in body
    assert body.get("token_type") == "Bearer"
    user = body["user"]
    assert user["email"] == "candidate@example.com"
    assert user["first_name"] == "Thomas"
    assert user["last_name"] == "Dupont"
    assert user["role"] == "user"
    assert user["is_active"] is True
    assert "id" in user
    set_cookie = response.headers["set-cookie"]
    assert "refresh_token=" in set_cookie
    assert "HttpOnly" in set_cookie
    assert "Secure" in set_cookie
    assert "samesite=lax" in set_cookie.lower()
    assert "Max-Age=604800" in set_cookie


@pytest.mark.asyncio
async def test_register_with_username_persists_and_returns_it_from_users_me(client, db_session):
    response = await client.post(
        "/api/v1/auth/register",
        json=_VALID_PAYLOAD | {
            "email": "john.doe@example.com",
            "username": "john.doe",
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["user"]["username"] == "john.doe"

    persisted = await db_session.scalar(
        select(UserModel).where(UserModel.id == UUID(body["user"]["id"]))
    )
    assert persisted is not None
    assert persisted.username == "john.doe"

    me_response = await client.get(
        "/api/v1/users/me",
        headers={"Authorization": f"Bearer {body['access_token']}"},
    )
    assert me_response.status_code == 200
    assert me_response.json()["username"] == "john.doe"


@pytest.mark.asyncio
async def test_register_without_username_returns_null(client):
    response = await client.post(
        "/api/v1/auth/register",
        json=_VALID_PAYLOAD | {"email": "no-username@example.com"},
    )

    assert response.status_code == 201
    assert response.json()["user"]["username"] is None


@pytest.mark.asyncio
async def test_register_returns_409_on_duplicate_username(client, create_user_in_db):
    await create_user_in_db(
        email="existing-username@example.com",
        username="john.doe",
    )

    response = await client.post(
        "/api/v1/auth/register",
        json=_VALID_PAYLOAD | {
            "email": "other@example.com",
            "username": "john.doe",
        },
    )

    assert response.status_code == 409
    assert response.json()["code"] == "username_already_exists"


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

    client.cookies.set("refresh_token", register_response.cookies.get("refresh_token"))
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


@pytest.mark.asyncio
async def test_register_returns_422_on_empty_first_name(client):
    """422 si first_name est une chaîne vide (min_length=1)."""
    response = await client.post(
        "/api/v1/auth/register",
        json=_VALID_PAYLOAD | {"email": "emptyfirst@example.com", "first_name": ""},
    )

    assert response.status_code == 422
    assert response.json()["code"] == "validation_error"


@pytest.mark.asyncio
async def test_register_returns_422_on_empty_last_name(client):
    """422 si last_name est une chaîne vide (min_length=1)."""
    response = await client.post(
        "/api/v1/auth/register",
        json=_VALID_PAYLOAD | {"email": "emptylast@example.com", "last_name": ""},
    )

    assert response.status_code == 422
    assert response.json()["code"] == "validation_error"


@pytest.mark.asyncio
async def test_register_returns_422_on_empty_password(client):
    """422 si le mot de passe est une chaîne vide (déclenche toutes les règles D4)."""
    response = await client.post(
        "/api/v1/auth/register",
        json=_VALID_PAYLOAD | {"email": "emptypwd@example.com", "password": ""},
    )

    assert response.status_code == 422
    assert response.json()["code"] == "validation_error"


@pytest.mark.asyncio
async def test_register_assigns_freemium_subscription(client, db_session):
    """Après inscription, une Subscription plan=FREEMIUM active est créée pour le Candidate."""
    from uuid import UUID

    from app.domain.billing.enums import Plan, SubscriptionStatus
    from app.infrastructure.persistence.repositories.subscription_sqlalchemy import (
        SubscriptionSQLAlchemyRepository,
    )

    response = await client.post(
        "/api/v1/auth/register",
        json=_VALID_PAYLOAD | {"email": "freemium@example.com"},
    )

    assert response.status_code == 201
    user_id = UUID(response.json()["user"]["id"])

    sub_repo = SubscriptionSQLAlchemyRepository(db_session)
    subscription = await sub_repo.get_by_user_id(user_id)

    assert subscription is not None
    assert subscription.plan == Plan.FREEMIUM
    assert subscription.status == SubscriptionStatus.ACTIVE
