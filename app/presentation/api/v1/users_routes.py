from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, status, Depends, Response

from app.application.billing.use_cases import AssignFreemiumOnSignupUseCase
from app.application.users.use_cases import UserService
from app.core.dependency import (
    UserServiceDep,
    AssignFreemiumDep
)
from app.domain.common.exceptions import NotFoundError
from app.presentation.api.mappers.users_mapper import to_user_read, to_domain_user
from app.presentation.api.v1.schemas.users import (
    UserRead,
    UsersCountResponse,
    UserCreate,
    UserUpdate
)
from app.presentation.security.deps import get_current_user_id, require_admin_role

CurrentUserIdDep = Annotated[UserRead, Depends(get_current_user_id)]

router = APIRouter(prefix="/users", tags=["users"])


@router.get(
    "",
    response_model=list[UserRead],
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_admin_role)],
    summary="List all users",
    description="Retrieve a list of all users in the system.",
    response_description="List of users",
)
async def list_users(
    service: UserServiceDep,
    skip: int = 0,
    limit: int = 50,
):
    """
    Endpoint to list all users with pagination.
    :param skip: Number of records to skip
    :param limit: Maximum number of records to return
    :param service: UserService instance
    :return: List of users
    """
    users = await service.list_users(skip=skip, limit=limit)
    return [to_user_read(user) for user in users]


@router.get(
    "/count",
    status_code=status.HTTP_200_OK,
    response_model=UsersCountResponse,
    dependencies=[Depends(require_admin_role)],
    summary="Get user count",
    description="Retrieve the total count of users in the system.",
    response_description="Total user count",
)
async def get_user_count(
    service: UserServiceDep,
) -> UsersCountResponse:
    """
    Endpoint to get the total count of users.
    :param service: UserService instance
    :return: Total user count
    """
    total = await service.count_users()
    return UsersCountResponse(total=total)

@router.get(
    "/me",
    status_code=status.HTTP_200_OK,
    summary="Get current user",
    description="Retrieve information about the currently authenticated user.",
    response_description="Current user information",
    responses={
        200: {"model": UserRead, "description": "Current user information"},
        404: {"description": "User not found"},
    }
)
async def get_me(
    current_user_id: CurrentUserIdDep,
    service: UserServiceDep,
):
    """
    Endpoint to get the current authenticated user's information.
    :param current_user_id: ID of the current user extracted from the JWT token
    :param service: UserService instance
    :return: User information or 404 if not found
    """
    user = await service.get_user_by_id(user_id=current_user_id)
    if not user:
        raise NotFoundError(
            code="user_not_found",
            details="User not found.",
        )
    return to_user_read(user)


@router.get(
    "/{user_id}",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_admin_role)],
    summary="Get user by ID",
    description="Retrieve a user by their ID.",
    response_description="The requested user",
    responses={
        200: {"model": UserRead, "description": "The requested user"},
        400: {"description": "Invalid user ID"},
        404: {"description": "User not found"},
    }
)
async def get_user_by_id(
    user_id: UUID,
    service: UserServiceDep,
) -> UserRead:
    user = await service.get_user_by_id(user_id=user_id)
    if not user:
        raise NotFoundError(code="user_not_found", details="User not found.")
    return to_user_read(user)


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    # dependencies=[Depends(require_admin_role)],
    summary="Create a new user",
    description="Create a new user in the system.",
    response_description="The created user",
    responses={
        201: {"model": UserRead, "description": "The created user"},
        400: {"description": "Invalid input data"},
    }
)
async def create_user(
    payload: UserCreate,
    service: UserServiceDep,
    assign_freemium: AssignFreemiumDep,
) -> UserRead:
    user = await service.register(
        email=str(payload.email),
        username=payload.username,
        first_name=payload.first_name,
        last_name=payload.last_name,
        password=payload.password,
        stripe_customer_id=payload.stripe_customer_id,
        role=payload.role,
        is_active=payload.is_active,
    )
    await assign_freemium.execute(user.id)
    return to_user_read(user)


@router.patch(
    "/{user_id}",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_admin_role)],
    summary="Update a user",
    description="Update an existing user in the system.",
    response_description="The updated user",
    responses={
        200: {"model": UserRead, "description": "The updated user"},
        400: {"description": "Invalid input data"},
        404: {"description": "User not found"},
    }
)
async def update_user(
    user_id: UUID,
    payload: UserUpdate,
    service: UserServiceDep,
) -> UserRead:
    updated_user = await service.update_user(
        user_id=user_id,
        partial_user=to_domain_user(payload)
    )
    return to_user_read(updated_user)


@router.delete(
    "/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_admin_role)],
    summary="Delete a user",
    description="Delete an existing user from the system.",
    responses={
        204: {"description": "User deleted successfully"},
        404: {"description": "User not found"},
    }
)
async def delete_user(
    user_id: UUID,
    service: UserServiceDep,
) -> Response:
    await service.delete_user(user_id=user_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
