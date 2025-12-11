from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from app.infrastructure.security.jwt_service import JWTTokenServiceAdapter

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/token")


def get_jwt_token_service() -> JWTTokenServiceAdapter:
    """Factory dependency returning a JWTTokenServiceAdapter instance."""
    return JWTTokenServiceAdapter()


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    jwt_service: JWTTokenServiceAdapter = Depends(get_jwt_token_service),
) -> str:
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
        payload = jwt_service.decode_token(token)
        user_id: str = payload.get("sub")
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return user_id
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
