from uuid import UUID

from fastapi import APIRouter, status, Depends, HTTPException

from app.application.users.use_cases import UserService
from app.core.dependency import get_user_service
from app.presentation.api.mappers.users_mapper import to_user_read
from app.presentation.api.v1.schemas.users import UserRead
from app.presentation.security.deps import get_current_user_id

router = APIRouter(prefix="/users", tags=["users"])


@router.get(
    "/me",
    status_code=status.HTTP_200_OK,
    response_model=UserRead,
    summary="Get current user",
    description="Retrieve information about the currently authenticated user.",
    response_description="Current user information",
)
async def get_me(
    current_user_id: UUID = Depends(get_current_user_id),
    service: UserService = Depends(get_user_service),
):
    """
    Endpoint to get the current authenticated user's information.
    :param current_user_id: ID of the current user extracted from the JWT token
    :param service: UserService instance
    :return: User information or 404 if not found
    """
    user = await service.get_user_by_id(user_id=current_user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    return to_user_read(user)
