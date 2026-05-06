import secrets
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm

from app.application.auth.use_cases import AuthService
from app.core.dependency import LinkedInOAuthUseCaseDep, UserRepositoryDep
from app.domain.common.exceptions import ConflictError, NotFoundError, UnauthorizedError
from app.infrastructure.security.jwt_service import JWTTokenServiceAdapter
from app.infrastructure.security.password_service import PasswordServiceAdapter
from app.presentation.api.v1.schemas.auth import (
    LinkedInAuthUrlResponse,
    LinkedInCallbackRequest,
    LinkedInCodeResponse,
    TokenPairSchema,
)
from app.presentation.security.deps import get_current_user_id

router = APIRouter(
    prefix="/auth",
    tags=["auth"],
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


@router.get(
    "/linkedin",
    response_model=LinkedInAuthUrlResponse,
    status_code=status.HTTP_200_OK,
    summary="Get LinkedIn OAuth authorization URL",
)
async def linkedin_auth_url(
    redirect_uri: str,
    use_case: LinkedInOAuthUseCaseDep,
) -> LinkedInAuthUrlResponse:
    """Return the LinkedIn authorization URL for the frontend to redirect the user to."""
    state = secrets.token_urlsafe(16)
    url = use_case.build_authorization_url(redirect_uri=redirect_uri, state=state)
    return LinkedInAuthUrlResponse(authorization_url=url)


@router.get(
    "/linkedin/callback",
    response_model=LinkedInCodeResponse,
    status_code=status.HTTP_200_OK,
    summary="LinkedIn OAuth redirect — returns code as JSON (dev helper)",
    description="LinkedIn redirects here after authorization. Returns the code and redirect_uri as JSON for easy copy-paste in Postman.",
)
async def linkedin_callback_get(code: str, state: str = "") -> LinkedInCodeResponse:
    """Dev helper: exposes the LinkedIn auth code as JSON instead of crashing with 422."""
    return LinkedInCodeResponse(
        code=code,
        redirect_uri="http://localhost:5001/api/v1/auth/linkedin/callback",
    )


@router.post(
    "/linkedin/callback",
    response_model=TokenPairSchema,
    status_code=status.HTTP_200_OK,
    summary="LinkedIn OAuth callback — exchange code for JWT",
)
async def linkedin_callback(
    body: LinkedInCallbackRequest,
    use_case: LinkedInOAuthUseCaseDep,
) -> TokenPairSchema:
    """Exchange the LinkedIn authorization code for a JobAI JWT pair."""
    try:
        tokens = await use_case.execute(code=body.code, redirect_uri=body.redirect_uri)
    except UnauthorizedError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=exc.details,
            headers={"WWW-Authenticate": "Bearer"},
        )
    return TokenPairSchema(
        access_token=tokens.access_token,
        refresh_token=tokens.refresh_token,
        token_type=tokens.token_type,
    )


@router.post(
    "/linkedin/link",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Link LinkedIn to an existing authenticated account",
)
async def linkedin_link(
    body: LinkedInCallbackRequest,
    use_case: LinkedInOAuthUseCaseDep,
    current_user_id: Annotated[UUID, Depends(get_current_user_id)],
) -> None:
    """Attach a LinkedIn identity to the currently authenticated user. Requires a valid JWT."""
    try:
        await use_case.link_to_existing_user(
            current_user_id=current_user_id,
            code=body.code,
            redirect_uri=body.redirect_uri,
        )
    except UnauthorizedError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=exc.details)
    except ConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=exc.details)
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=exc.details)
