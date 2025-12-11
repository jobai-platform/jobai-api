from dataclasses import dataclass
from typing import Optional

from app.application.auth.ports import TokenService
from app.application.users.ports import UserRepository, PasswordHasher
from app.domain.users.entities import User


@dataclass
class AuthTokens:
    access_token: str
    refresh_token: str
    token_type: str = 'Bearer'


class AuthService:

    def __init__(
        self,
        user_repo: UserRepository,
        pwd_hasher: PasswordHasher,
        token_service: TokenService,
    ) -> None:
        self.user_repo = user_repo
        self.pwd_hasher = pwd_hasher
        self.token_service = token_service


    async def login(self, email: str, password: str) -> AuthTokens:
        user: Optional[User] = await self.user_repo.get_by_email(email)

        if user is None or not user.hashed_password:
            raise ValueError("Invalid email or password")

        if not self.pwd_hasher.verify(password, user.hashed_password):
            raise ValueError("Invalid email or password")

        subject = str(user.id)

        access_token = self.token_service.create_access_token(
            subject=subject,
            extra={"role": user.role},
        )
        refresh_token = self.token_service.create_refresh_token(
            subject=subject,
            extra={"role": user.role},
        )

        return AuthTokens(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="Bearer",
        )
