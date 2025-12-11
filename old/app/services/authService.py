from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from old.app.repository.authRepository import AuthRepository
from old.app.utils.jwt_service import PasswordService, JWTService


class AuthService:
    """Service class for authentication-related operations."""

    def __init__(
        self,
        repo: AuthRepository | None = None,
        pwd: PasswordService | None = None,
        jwt: JWTService | None = None
    ) -> None:
        self.repo = repo or AuthRepository()
        self.pwd = pwd or PasswordService()
        self.jwt = jwt or JWTService()


    async def login(
        self,
        session: AsyncSession,
        email: str,
        password: str
    ) -> dict:
        """
        Authenticate user and return JWT tokens.
        Raises HTTPException if authentication fails.
        :raises HTTPException: If authentication fails.
        :param session: AsyncSession
        :param email: User's email
        :param password: User's password
        :return: dict containing access and refresh tokens
        """
        user = await self.repo.get_user_with_password(session, email)

        if user is None or not self.pwd.verify_password(password, user.hashed_password or ""):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )

        access_token = self.jwt.create_access_token({"sub": str(user.id)})
        refresh_token = self.jwt.create_refresh_token({"sub": str(user.id)})

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer"
        }
