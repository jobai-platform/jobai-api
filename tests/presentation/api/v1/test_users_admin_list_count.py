import pytest


@pytest.mark.asyncio
async def test_admin_list_users_returns_401_without_token(client):
    response = await client.get("/api/v1/users")
    assert response.status_code == 401
    data = response.json()
    assert data["code"] == "invalid_authentication"


@pytest.mark.asyncio
async def test_admin_list_users_returns_403_for_non_admin(client, create_user_in_db, jwt_service):
    user = await create_user_in_db(role="user", email="user1@fakemail.com", password="userpass")
    token = jwt_service.create_access_token(
        subject=str(user.id),
        extra={"role": user.role, "email": user.email},
    )

    response = await client.get(
        "/api/v1/users",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 403
    data = response.json()
    assert data["code"] == "insufficient_permissions"


@pytest.mark.asyncio
async def test_admin_list_users_returns_200_and_items(client, create_user_in_db, jwt_service):
    admin_user = await create_user_in_db(role="admin", email="admin@fakemail.com", password="adminpass")
    await create_user_in_db(role="user", email="user1@fakemail.com", password="user1pass")
    await create_user_in_db(role="user", email="user2@fakemail.com", password="user2pass")

    token = jwt_service.create_access_token(
        subject=str(admin_user.id),
        extra={"role": admin_user.role, "email": admin_user.email},
    )

    response = await client.get(
        "/api/v1/users?skip=0&limit=10",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 3

    # Check that at least the created users are in the list
    assert "id" in data[0]
    assert "email" in data[0]
    assert "role" in data[0]
    assert "is_active" in data[0]


@pytest.mark.asyncio
async def test_admin_list_users_respects_pagination(client, create_user_in_db, jwt_service):
    admin_user = await create_user_in_db(email="admin2@example.com", password="secret", role="admin")
    await create_user_in_db(email="user1@example.com", password="secret1", role="user")
    await create_user_in_db(email="user2@example.com", password="secret2", role="user")
    await create_user_in_db(email="user3@example.com", password="secret3", role="user")

    token = jwt_service.create_access_token(
        subject=str(admin_user.id),
        extra={"role": "admin", "email": admin_user.email},
    )

    response = await client.get(
        "/api/v1/users?skip=1&limit=2",
        headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 2
