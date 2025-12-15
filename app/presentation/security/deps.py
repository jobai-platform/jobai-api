from typing import Any, Mapping
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from app.domain.common.exceptions import UnauthorizedError, ForbiddenError
from app.infrastructure.security.jwt_service import JWTTokenServiceAdapter

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/api/v1/auth/token",
    auto_error=False,
)


def get_jwt_token_service() -> JWTTokenServiceAdapter:
    """Factory dependency returning a JWTTokenServiceAdapter instance."""
    return JWTTokenServiceAdapter()


def _unauthorized() -> None:
    # Keep message stable for existing tests/clients
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
    token: str = Depends(oauth2_scheme),
    jwt_service: JWTTokenServiceAdapter = Depends(get_jwt_token_service),
) -> dict[str, Any]:
    """
    Dependency to get the current JWT claims from the token.
    Expected:
        - sub: UUID of the user
        - role: Role of the user
        - email: Email of the user (optional)
    :param token: JWT token from the request
    :param jwt_service: JWTTokenServiceAdapter instance
    :return: User ID extracted from the token
    """
    if not token:
        _unauthorized()

    try:
        return dict(jwt_service.decode_token(token))
    except Exception:
        _unauthorized()


async def get_current_user_id(claims: Mapping[str, Any] = Depends(get_current_claims)) -> UUID:
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


async def get_current_user_role(claims: Mapping[str, Any] = Depends(get_current_claims)) -> str:
    """
    Dependency to get the current user role from the JWT claims.
    :param claims: JWT claims from the token
    :return: User role extracted from the claims
    """
    role = claims.get("role")
    if not role:
        _unauthorized()
    return str(role)


async def get_current_user_email(claims: Mapping[str, Any] = Depends(get_current_claims)) -> str | None:
    """
    Dependency to get the current user email from the JWT claims.
    :param claims: JWT claims from the token
    :return: User email extracted from the claims
    """
    email = claims.get("email")
    return str(email) if email else None


async def require_admin_role(
    role: str = Depends(get_current_user_role)
):
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
    async def _guard(
        role: str = Depends(get_current_user_role)
    ) -> None:
        if role not in allowed_roles:
            _forbidden()

    return _guard
