import uuid
import pytest


# @pytest.mark.asyncio
# async def test_admin_create_user_returns_401_without_token(client):
#     response = await client.post(
#         "/api/v1/users",
#         json={
#             "email": "user@fakemail.com",
#             "password": "securepassword",
#         }
#     )
#     assert response.status_code == 401
#     assert response.json()["code"] == "invalid_authentication"


# @pytest.mark.asyncio
# async def test_admin_create_user_returns_403_for_non_admin(client, create_user_in_db, jwt_service):
#     user = await create_user_in_db(
#         email="user@fakemail.com",
#         password="securepassword",
#         role="user"
#     )
#     token = jwt_service.create_access_token(
#         subject=str(user.id),
#         extra={"role": user.role, "email": user.email}
#     )
#
#     response = await client.post(
#         "/api/v1/users",
#         headers={"Authorization": f"Bearer {token}"},
#         json={
#             "email": "user1@fakemail.com",
#             "password": "securepassword",
#         }
#     )
#     assert response.status_code == 403
#     assert response.json()["code"] == "insufficient_permissions"


@pytest.mark.asyncio
async def test_admin_create_user_returns_201(client, create_user_in_db, jwt_service, freemium_price_in_db):
    admin_user = await create_user_in_db(
        email="admin@fakemail.com",
        password="securepassword",
        role="admin"
    )
    token = jwt_service.create_access_token(
        subject=str(admin_user.id),
        extra={"role": admin_user.role, "email": admin_user.email}
    )

    response = await client.post(
        "/api/v1/users",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "email": "newuser@fakemail.com",
            "password": "securepassword",
            "role": "user",
            "is_active": True,
        },
    )

    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "newuser@fakemail.com"
    assert data["role"] == "user"
    assert data["is_active"] is True
    assert "id" in data


@pytest.mark.asyncio
async def test_admin_create_user_returns_409_if_email_exists(client, create_user_in_db, jwt_service):
    admin_user = await create_user_in_db(
        email="admin@fakemail.com",
        password="securepassword",
        role="admin",
    )
    await create_user_in_db(
        email="user@fakemail.com",
        password="securepassword",
        role="user",
    )
    token = jwt_service.create_access_token(
        subject=str(admin_user.id),
        extra={"role": admin_user.role, "email": admin_user.email}
    )

    response = await client.post(
        "/api/v1/users",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "email": "USER@fakemail.com",  # Testing case insensitivity
            "password": "securepassword",
        }
    )
    assert response.status_code == 409
    assert response.json()["code"] == "user_already_exists"


@pytest.mark.asyncio
async def test_admin_update_user_returns_404_for_nonexistent_user(client, create_user_in_db, jwt_service):
    admin_user = await create_user_in_db(
        email="admin@fakemail.com",
        password="securepassword",
        role="admin",
    )
    token = jwt_service.create_access_token(
        subject=str(admin_user.id),
        extra={"role": admin_user.role, "email": admin_user.email}
    )

    response = await client.patch(
        f"/api/v1/users/{uuid.uuid4()}",
        headers={"Authorization": f"Bearer {token}"},
        json={"first_name": "UpdatedName"}
    )
    assert response.status_code == 404
    assert response.json()["code"] == "user_not_found"


@pytest.mark.asyncio
async def test_admin_update_user_returns_200(client, create_user_in_db, jwt_service):
    admin_user = await create_user_in_db(
        email="admin@fakemail.com",
        password="securepassword",
        role="admin",
    )
    target = await create_user_in_db(email="target@fakemail.com", password="secret", role="user")
    token = jwt_service.create_access_token(
        subject=str(admin_user.id),
        extra={"role": admin_user.role, "email": admin_user.email}
    )

    user_to_update = await client.patch(
        f"/api/v1/users/{target.id}",
        headers={"Authorization": f"Bearer {token}"},
        json={"first_name": "UpdatedName", "role": "admin", "is_active": False},
    )
    assert user_to_update.status_code == 200
    data = user_to_update.json()
    assert data["first_name"] == "UpdatedName"
    assert data["role"] == "admin"
    assert data["is_active"] is False


@pytest.mark.asyncio
async def test_admin_delete_user_returns_204(client, create_user_in_db, jwt_service):
    admin_user = await create_user_in_db(
        email="admin@fakemail.com",
        password="securepassword",
        role="admin",
    )
    target = await create_user_in_db(email="target@fakemail.com", password="secret", role="user")
    token = jwt_service.create_access_token(
        subject=str(admin_user.id),
        extra={"role": admin_user.role, "email": admin_user.email}
    )

    response = await client.delete(
        f"/api/v1/users/{target.id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 204

    # Verify user is deleted
    get_response = await client.get(
        f"/api/v1/users/{target.id}",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert get_response.status_code == 404


@pytest.mark.asyncio
async def test_admin_delete_user_returns_404_for_nonexistent_user(client, create_user_in_db, jwt_service):
    admin_user = await create_user_in_db(
        email="admin@fakemail.com",
        password="securepassword",
        role="admin",
    )
    token = jwt_service.create_access_token(
        subject=str(admin_user.id),
        extra={"role": admin_user.role, "email": admin_user.email}
    )
    response = await client.delete(
        f"/api/v1/users/{uuid.uuid4()}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 404
    assert response.json()["code"] == "user_not_found"
