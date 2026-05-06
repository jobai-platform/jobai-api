from dataclasses import dataclass
from typing import Optional

from app.application.auth.ports import TokenService
from app.application.users.ports import PasswordHasher, UserRepository
from app.domain.users.entities import User
from app.domain.users.value_objects import Email


@dataclass
class TokenPair:
    access_token: str
    refresh_token: str
    token_type: str = "Bearer"


class AuthService:
    """
    Service for handling authentication-related use cases.
    """
    def __init__(
        self,
        user_repo: UserRepository,
        pwd_hasher: PasswordHasher,
        token_service: TokenService,
    ) -> None:
        self.user_repo = user_repo
        self.pwd_hasher = pwd_hasher
        self.token_service = token_service


    async def login(self, email: str | Email, password: str) -> TokenPair:
        """
        Authenticate a user and return auth tokens.
        :param email: email of the user
        :param password: password of the user
        :return: AuthTokens object containing access and refresh tokens
        """
        email_vo = email if isinstance(email, Email) else Email.from_raw(email)

        user: Optional[User] = await self.user_repo.get_by_email(email_vo)
        if (not user or
            not user.hashed_password or
            not self.pwd_hasher.verify(password, user.hashed_password)
        ):
            raise ValueError("Invalid credentials")

        if not user.is_active:
            raise ValueError("User account is inactive")

        subject = str(user.id)
        extra = {
            "role": user.role,
            "email": str(user.email),
        }

        access_token = self.token_service.create_access_token(
            subject=subject,
            extra=extra,
        )
        refresh_token = self.token_service.create_refresh_token(
            subject=subject,
            extra=extra,
        )

        return TokenPair(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="Bearer",
        )
