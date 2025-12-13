from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from app.infrastructure.security.jwt_service import JWTTokenServiceAdapter

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/token")


def get_jwt_token_service() -> JWTTokenServiceAdapter:
    """Factory dependency returning a JWTTokenServiceAdapter instance."""
    return JWTTokenServiceAdapter()


async def get_current_claims(
    token: str = Depends(oauth2_scheme),
    jwt_service: JWTTokenServiceAdapter = Depends(get_jwt_token_service),
) -> dict:
    """
    Dependency to get the current user from the JWT token.
    :param token: JWT token from the request
    :param jwt_service: JWTTokenServiceAdapter instance
    :return: User ID extracted from the token
    """
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        return dict(jwt_service.decode_token(token))
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_user_id(claims: dict = Depends(get_current_claims)) -> UUID:
    """
    Dependency to get the current user ID from the JWT claims.
    :param claims: JWT claims from the token
    :return: User ID extracted from the claims
    """
    sub = claims.get("sub")
    try:
        return UUID(str(sub))
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_user_role(claims: dict = Depends(get_current_claims)) -> str:
    """
    Dependency to get the current user role from the JWT claims.
    :param claims: JWT claims from the token
    :return: User role extracted from the claims
    """
    role = claims.get("role")
    if not role:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return str(role)


async def require_admin_role(
    role: str = Depends(get_current_user_role)
):
    """
    Dependency to ensure the current user has admin role.
    :param role: User role extracted from the claims
    :raises HTTPException: If the user does not have admin role
    """
    if role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions",
        )
