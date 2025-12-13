import uuid
import pytest


@pytest.mark.asyncio
async def test_get_me_returns_401_without_authentication(client):
    response = await client.get("/api/v1/users/me")
    assert response.status_code == 401
    assert "detail" in response.json()


@pytest.mark.asyncio
async def test_get_me_returns_404_for_nonexistent_user(client, jwt_service):
    token = jwt_service.create_access_token(
        subject=str(uuid.uuid4()),
        extra={"role": "user", "email": "ghost@example.com"},
    )

    response = await client.get(
        "/api/v1/users/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 404
    assert response.json() == {
        "detail": "User not found"
    }


@pytest.mark.asyncio
async def test_get_me_returns_current_user(client, create_user_in_db, jwt_service):
    user = await create_user_in_db(
        email="me@example.com",
        password="securepassword",
        role="user",
    )

    token = jwt_service.create_access_token(
        subject=str(user.id),
        extra={"role": "user", "email": user.email},
    )

    response = await client.get(
        "/api/v1/users/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(user.id)
    assert data["email"] == "me@example.com"
