from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_session
from app.core.dependency import get_user_service
from app.schemas.UserSchemas import UserRead, UserCreate, UserUpdate
from app.services.usersService import UserService

router = APIRouter(prefix="/users", tags=["Users"])


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    summary="Create a new user",
    description="Create a new user with the provided information.",
    responses={
        201: {"description": "User created successfully."},
        400: {"description": "Bad request."},
        500: {"description": "Internal server error."},
    },
    response_model=UserRead
)
async def create_user(
    payload: UserCreate,
    session: AsyncSession = Depends(get_async_session),
    user_service: UserService = Depends(get_user_service),
):
    """Create a new user."""
    try:
        return await user_service.register(session, payload)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get(
    "/{user_id}",
    status_code=status.HTTP_200_OK,
    summary="Get user by ID",
    description="Retrieve a user by their unique ID.",
    responses={
        200: {"description": "User retrieved successfully."},
        404: {"description": "User not found."},
        500: {"description": "Internal server error."},
    },
    response_model=UserRead
)
async def get_user(
    user_id: UUID,
    session: AsyncSession = Depends(get_async_session),
    user_service: UserService = Depends(get_user_service),
):
    """Retrieve a user by their ID."""
    try:
        user = await user_service.get(session, user_id)
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found."
            )
        return user
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.patch(
    "/{user_id}",
    status_code=status.HTTP_200_OK,
    summary="Update user by ID",
    description="Update an existing user with the provided information.",
    responses={
        200: {"description": "User updated successfully."},
        400: {"description": "Bad request."},
        404: {"description": "User not found."},
        500: {"description": "Internal server error."},
    },
    response_model=UserRead
)
async def update_user(
    user_id: UUID,
    payload: UserUpdate,
    session: AsyncSession = Depends(get_async_session),
    user_service: UserService = Depends(get_user_service),
):
    """Update an existing user."""
    try:
        updated_user = await user_service.update(user_id, payload, session)
        if updated_user is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found."
            )
        return updated_user
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.delete(
    "/{user_id}",
    status_code=status.HTTP_200_OK,
    summary="Delete user by ID",
    description="Delete a user by their unique ID.",
    responses={
        200: {"description": "User deleted successfully."},
        404: {"description": "User not found."},
        500: {"description": "Internal server error."},
    },
)
async def delete_user(
    user_id: UUID,
    session: AsyncSession = Depends(get_async_session),
    user_service: UserService = Depends(get_user_service),
):
    """Delete a user by their ID."""
    try:
        await user_service.delete(user_id, session)
        return {"message": "User deleted successfully."}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
