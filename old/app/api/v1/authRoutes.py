from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from old.app.core.database import get_async_session
from old.app.schemas.authSchemas import RegisterResponse
from old.app.services.authService import AuthService

router = APIRouter(prefix="/auth", tags=["auth"], version="1.0")


# User register Route
# @router.post(
#     "/register",
#     response_model=RegisterResponse,
#     status_code=status.HTTP_201_CREATED,
#     summary="Register a new user",
#     description="Register a new user with the provided information.",
#     responses={
#         201: {"description": "User registered successfully."},
#         400: {"description": "Bad request."},
#         500: {"description": "Internal server error."},
#     },
# )
# async def register_user(
#     user_data: UserCreate,
# )

@router.post(
    "/token",
    summary="User login",
    description="Authenticate user and return JWT tokens.",
    responses={
        200: {"description": "Login successful."},
        401: {"description": "Unauthorized."},
        500: {"description": "Internal server error."},
    },
)
async def login(
    email: str,
    password: str,
    session: AsyncSession = Depends(get_async_session),
    auth_service: AuthService = Depends()
):
    """Authenticate user and return JWT tokens."""
    try:
        return await auth_service.login(session, email, password)
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
