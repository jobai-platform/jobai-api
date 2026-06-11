import secrets
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.security import OAuth2PasswordRequestForm

from app.application.auth.use_cases import AuthService
from app.core.config import settings
from app.core.dependency import (
    ForgotPasswordUseCaseDep,
    LinkedInCallbackUseCaseDep,
    LinkedInOAuthUseCaseDep,
    LogoutUseCaseDep,
    RefreshTokenUseCaseDep,
    RegisterUseCaseDep,
    ResetPasswordUseCaseDep,
    UserRepositoryDep,
)
from app.core.rate_limiting import limiter
from app.domain.common.exceptions import ConflictError, NotFoundError, UnauthorizedError
from app.infrastructure.security.jwt_service import JWTTokenServiceAdapter
from app.infrastructure.security.password_service import PasswordServiceAdapter
from app.presentation.api.mappers.users_mapper import to_candidate_read as to_user_read
from app.presentation.api.v1.schemas.auth import (
    AccessTokenResponse,
    ForgotPasswordRequest,
    LinkedInAuthUrlResponse,
    LinkedInCallbackRequest,
    LinkedInCallbackResponse,
    LinkedInCodeResponse,
    RegisterRequest,
    RegisterResponse,
    ResetPasswordRequest,
)
from app.presentation.security.deps import get_current_user_id

router = APIRouter(
    prefix="/auth",
    tags=["auth"],
)

REFRESH_TOKEN_COOKIE_NAME = "refresh_token"
REFRESH_TOKEN_COOKIE_MAX_AGE_SECONDS = 7 * 24 * 60 * 60


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
    "/register",
    response_model=RegisterResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new Candidate account",
    description=(
        "Create a Candidate account."
        " Returns access_token in body; refresh_token via httpOnly cookie."
    ),
)
@limiter.limit("5/minute")
async def register(
    request: Request,
    body: RegisterRequest,
    response: Response,
    use_case: RegisterUseCaseDep,
) -> RegisterResponse:
    result = await use_case.execute(
        email=body.email,
        username=body.username,
        password=body.password,
        first_name=body.first_name,
        last_name=body.last_name,
    )
    response.set_cookie(
        REFRESH_TOKEN_COOKIE_NAME,
        result.tokens.refresh_token,
        max_age=REFRESH_TOKEN_COOKIE_MAX_AGE_SECONDS,
        httponly=True,
        secure=True,
        samesite="lax",
        path="/",
    )
    return RegisterResponse(
        user=to_user_read(result.candidate),
        access_token=result.tokens.access_token,
    )


@router.post(
    "/token",
    response_model=AccessTokenResponse,
    status_code=status.HTTP_200_OK,
    summary="User login and obtain JWT tokens",
    description=(
        "Authenticate user and return JWT access token. Refresh token is set in an httpOnly cookie."
    ),
)
async def login(
    response: Response,
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    auth_service: AuthServiceDep,
):
    """
    Oauth2-compatible login, get an access token and a refresh token for future requests.
    :param response: FastAPI Response to set cookies
    :param form_data: OAuth2PasswordRequestForm
    :param auth_service: AuthService
    :return: AccessTokenResponse
    """
    try:
        tokens = await auth_service.login(
            email=form_data.username,
            password=form_data.password,
        )
        response.set_cookie(
            REFRESH_TOKEN_COOKIE_NAME,
            tokens.refresh_token,
            max_age=REFRESH_TOKEN_COOKIE_MAX_AGE_SECONDS,
            httponly=True,
            secure=True,
            samesite="lax",
            path="/",
        )
        return AccessTokenResponse(
            access_token=tokens.access_token,
            token_type=tokens.token_type,
        )
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        ) from None


@router.post(
    "/refresh",
    response_model=AccessTokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Refresh access token from the httpOnly refresh cookie",
)
async def refresh_session(
    request: Request,
    response: Response,
    use_case: RefreshTokenUseCaseDep,
) -> AccessTokenResponse:
    refresh_token = request.cookies.get(REFRESH_TOKEN_COOKIE_NAME)
    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    tokens = await use_case.execute(refresh_token)
    response.set_cookie(
        REFRESH_TOKEN_COOKIE_NAME,
        tokens.refresh_token,
        max_age=REFRESH_TOKEN_COOKIE_MAX_AGE_SECONDS,
        httponly=True,
        secure=True,
        samesite="lax",
        path="/",
    )
    return AccessTokenResponse(access_token=tokens.access_token, token_type=tokens.token_type)


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Logout by revoking and expiring the refresh cookie",
)
async def logout(
    request: Request,
    response: Response,
    use_case: LogoutUseCaseDep,
) -> None:
    refresh_token = request.cookies.get(REFRESH_TOKEN_COOKIE_NAME)
    if refresh_token:
        await use_case.execute(refresh_token)

    response.delete_cookie(
        REFRESH_TOKEN_COOKIE_NAME,
        path="/",
        httponly=True,
        secure=True,
        samesite="lax",
    )
    return None


@router.post(
    "/password/forgot",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Request a Candidate password reset email",
    description="Returns the same response whether or not the Candidate account exists.",
)
@limiter.limit("5/minute")
async def forgot_password(
    request: Request,
    body: ForgotPasswordRequest,
    use_case: ForgotPasswordUseCaseDep,
) -> None:
    reset_base_url = f"{settings.FRONTEND_ORIGIN.rstrip('/')}/auth/password/reset"
    await use_case.execute(email=str(body.email), reset_base_url=reset_base_url)


@router.post(
    "/password/reset",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Reset a Candidate password with a single-use token",
)
async def reset_password(
    body: ResetPasswordRequest,
    use_case: ResetPasswordUseCaseDep,
) -> None:
    try:
        await use_case.execute(
            signed_token=body.token,
            new_password=body.new_password,
        )
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired password reset token",
        ) from None


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
    """Return the LinkedIn authorization URL and state token for CSRF verification."""
    state = secrets.token_urlsafe(16)
    url = use_case.build_authorization_url(redirect_uri=redirect_uri, state=state)
    return LinkedInAuthUrlResponse(authorization_url=url, state=state)


@router.get(
    "/linkedin/callback",
    response_model=LinkedInCodeResponse,
    status_code=status.HTTP_200_OK,
    summary="LinkedIn OAuth redirect — returns code as JSON (dev helper)",
    description=(
        "LinkedIn redirects here after authorization. Returns the code and redirect_uri as JSON "
        "for easy copy-paste in Postman."
    ),
)
async def linkedin_callback_get(code: str, state: str = "") -> LinkedInCodeResponse:
    """Dev helper: exposes the LinkedIn auth code as JSON instead of crashing with 422."""
    return LinkedInCodeResponse(
        code=code,
        redirect_uri=settings.LINKEDIN_REDIRECT_URI,
    )


@router.post(
    "/linkedin/callback",
    response_model=LinkedInCallbackResponse,
    status_code=status.HTTP_200_OK,
    summary="LinkedIn OAuth callback — exchange code for JWT",
)
async def linkedin_callback(
    body: LinkedInCallbackRequest,
    response: Response,
    use_case: LinkedInCallbackUseCaseDep,
) -> LinkedInCallbackResponse:
    """Exchange the LinkedIn authorization code for a JWT. Sets refresh_token as httpOnly cookie."""
    result = await use_case.execute(code=body.code, redirect_uri=body.redirect_uri)
    response.set_cookie(
        REFRESH_TOKEN_COOKIE_NAME,
        result.refresh_token,
        max_age=REFRESH_TOKEN_COOKIE_MAX_AGE_SECONDS,
        httponly=True,
        secure=True,
        samesite="lax",
        path="/",
    )
    return LinkedInCallbackResponse(
        access_token=result.access_token,
        is_new_user=result.is_new_user,
        token_type=result.token_type,
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
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=exc.details) from exc
    except ConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=exc.details) from exc
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=exc.details) from exc
