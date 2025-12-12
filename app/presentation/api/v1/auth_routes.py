from fastapi import APIRouter, Depends, status, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.auth.use_cases import AuthService
from app.infrastructure.config.database import get_async_session
from app.infrastructure.persistence.repositories.user_sqlalchemy import SqlAlchemyUserRepository
from app.infrastructure.security.jwt_service import JWTTokenServiceAdapter
from app.infrastructure.security.password_service import PasswordServiceAdapter
from app.schemas.auth_schemas import TokenPairSchema

router = APIRouter(
    prefix="/auth",
    tags=["auth"]
)


async def get_auth_service(
    session: AsyncSession = Depends(get_async_session),
) -> AuthService:
    user_repo = SqlAlchemyUserRepository(session=session)
    pwd_hasher = PasswordServiceAdapter()
    token_service = JWTTokenServiceAdapter()

    return AuthService(
        user_repo=user_repo,
        pwd_hasher=pwd_hasher,
        token_service=token_service,
    )


@router.post(
    "/token",
    response_model=TokenPairSchema,
    status_code=status.HTTP_200_OK,
    summary="User login and obtain JWT tokens",
    description="Authenticate user and return JWT access and refresh tokens.",
)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    auth_service: AuthService = Depends(get_auth_service),
):
    """
    Oauth2-compatible login, get an access token and a refresh token for future requests.
    :param form_data: OAuth2PasswordRequestForm
    :param form_data.username: str
    :param form_data.password: str
    :param auth_service: AuthService
    :return: TokenPair
    """
    email = form_data.username
    password = form_data.password

    try:
        tokens = await auth_service.login(email=email, password=password)
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
