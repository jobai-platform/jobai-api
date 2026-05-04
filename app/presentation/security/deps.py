from typing import Any, Mapping, Annotated
from uuid import UUID

from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from starlette.requests import Request

from app.domain.common.exceptions import UnauthorizedError, ForbiddenError
from app.infrastructure.security.jwt_service import JWTTokenServiceAdapter

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/api/v1/auth/token",
    auto_error=False,
)


def get_jwt_token_service() -> JWTTokenServiceAdapter:
    return JWTTokenServiceAdapter()

JWTServiceDep = Annotated[JWTTokenServiceAdapter, Depends(get_jwt_token_service)]
TokenDep = Annotated[str, Depends(oauth2_scheme)]


def _unauthorized() -> None:
    raise UnauthorizedError(
        code="invalid_authentication",
        details="Invalid authentication credentials",
    )


def _forbidden() -> None:
    raise ForbiddenError(
        code="insufficient_permissions",
        details="Insufficient permissions",
    )


async def get_current_claims(
    request: Request,
    token: TokenDep,
    jwt_service: JWTServiceDep,
) -> dict[str, Any]:
    """
    Dependency to get the current JWT claims from the token.
    Expected:
        - sub: UUID of the user
        - role: Role of the user
        - email: Email of the user (optional)
    :param request: Starlette Request object
    :param token: JWT token from the request
    :param jwt_service: JWTTokenServiceAdapter instance
    :return: User ID extracted from the token
    """
    if not token:
        _unauthorized()

    try:
        claims = jwt_service.decode_token(token)
        request.state.jwt_claims = claims
        request.state.user_id = claims.get("sub")
        request.state.user_role = claims.get("role")
        request.state.user_email = claims.get("email")
        return claims
    except Exception:
        _unauthorized()


ClaimsDep = Annotated[dict[str, Any], Depends(get_current_claims)]

async def get_current_user_id(claims: ClaimsDep) -> UUID:
    """
    Dependency to get the current user ID from the JWT claims.
    :param claims: JWT claims from the token
    :return: User ID extracted from the claims
    """
    sub = claims.get("sub")
    if not sub:
        _unauthorized()

    try:
        return UUID(str(sub))
    except Exception:
        _unauthorized()


async def get_current_user_role(claims:ClaimsDep) -> str:
    """
    Dependency to get the current user role from the JWT claims.
    :param claims: JWT claims from the token
    :return: User role extracted from the claims
    """
    role = claims.get("role")
    if not role:
        _unauthorized()
    return str(role)


async def get_current_user_email(claims:ClaimsDep) -> str | None:
    """
    Dependency to get the current user email from the JWT claims.
    :param claims: JWT claims from the token
    :return: User email extracted from the claims
    """
    email = claims.get("email")
    return str(email) if email else None

UserRoleDep = Annotated[str, Depends(get_current_user_role)]


async def require_admin_role(role: UserRoleDep) -> None:
    """
    Dependency to ensure the current user has admin role.
    :param role: User role extracted from the claims
    :raises HTTPException: If the user does not have admin role
    """
    if role != "admin":
        _forbidden()


async def require_user_role(*allowed_roles: str):
    """
    Future-proof guard.
    Usage:
        dependencies=[Depends(require_user_role('admin', 'user', 'moderator))]
    :param allowed_roles: Allowed roles
    :return:
    """
    async def _guard(role: UserRoleDep) -> None:
        if role not in allowed_roles:
            _forbidden()

    return _guard
