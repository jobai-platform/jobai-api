from abc import abstractmethod


class AuthRepositoryInterface:

    @abstractmethod
    async def login(self, email: str, password: str) -> dict: ...

    @abstractmethod
    async def refresh(self, refresh_token: str) -> dict: ...

    @abstractmethod
    async def logout(self, user_id: int) -> None: ...

    @abstractmethod
    async def verify_token(self, token: str) -> dict: ...

    @abstractmethod
    async def revoke_token(self, token: str) -> None: ...

    @abstractmethod
    async def is_token_revoked(self, token: str) -> bool: ...

    @abstractmethod
    async def get_user_with_password(self, email: str) -> dict | None: ...
