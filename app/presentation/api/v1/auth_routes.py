from typing import Annotated

from fastapi import APIRouter, Depends, status, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.auth.use_cases import AuthService
from app.core.dependency import UserRepositoryDep
from app.infrastructure.persistence.repositories.user_sqlalchemy import SqlAlchemyUserRepository
from app.infrastructure.security.jwt_service import JWTTokenServiceAdapter
from app.infrastructure.security.password_service import PasswordServiceAdapter
from app.presentation.api.v1.schemas.auth import TokenPairSchema

router = APIRouter(
    prefix="/auth",
    tags=["auth"]
)


def get_auth_service(
    repo: UserRepositoryDep,
) -> AuthService:
    return AuthService(
        user_repo=repo,
        pwd_hasher=PasswordServiceAdapter(),
        token_service=JWTTokenServiceAdapter(),
    )

AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]

@router.post(
    "/token",
    response_model=TokenPairSchema,
    status_code=status.HTTP_200_OK,
    summary="User login and obtain JWT tokens",
    description="Authenticate user and return JWT access and refresh tokens.",
)
async def login(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    auth_service: AuthServiceDep,
):
    """
    Oauth2-compatible login, get an access token and a refresh token for future requests.
    :param form_data: OAuth2PasswordRequestForm
    :param auth_service: AuthService
    :return: TokenPair
    """
    try:
        tokens = await auth_service.login(
            email=form_data.username,
            password=form_data.password,
        )
        return TokenPairSchema(
            access_token=tokens.access_token,
            refresh_token=tokens.refresh_token,
            token_type=tokens.token_type,
        )
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
