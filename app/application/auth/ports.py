from abc import ABC, abstractmethod
from collections.abc import Mapping

from app.domain.users.refresh_token import RefreshToken
from app.domain.users.value_objects import LinkedInProfile


class LinkedInOAuthGateway(ABC):
    """
    Port for exchanging a LinkedIn OAuth authorization code for a normalized user profile.
    Concrete implementation: LinkedInOAuthAdapter.
    """

    @abstractmethod
    async def exchange_code(self, code: str, redirect_uri: str) -> LinkedInProfile:
        """
        Exchange a LinkedIn OAuth authorization code for a LinkedInProfile.
        Raises UnauthorizedError if the code is invalid or expired.
        """
        raise NotImplementedError

    @abstractmethod
    def build_authorization_url(self, redirect_uri: str, state: str) -> str:
        """
        Build the LinkedIn authorization URL to redirect the user to.
        """
        raise NotImplementedError


class TokenService(ABC):
    """ Abstract class to implement JWT and Token authentication """

    @abstractmethod
    def create_access_token(
        self,
        subject: str,
        extra: Mapping[str, object] | None = None,
    ) -> str:
        raise NotImplementedError

    @abstractmethod
    def create_refresh_token(
        self,
        subject: str,
        extra: Mapping[str, object] | None = None,
    ) -> str:
        raise NotImplementedError

    @abstractmethod
    def decode_token(
        self,
        token: str,
    ) -> Mapping[str, object]:
        raise NotImplementedError

    @abstractmethod
    def validate_refresh_token(self, token: str) -> str:
        """
        Validate that token is a non-expired refresh token.
        Returns the subject (user_id). Raises UnauthorizedError otherwise.
        """
        raise NotImplementedError


class RefreshTokenRepository(ABC):
    """Port for refresh token persistence keyed by token_hash (SHA-256 of raw JWT)."""

    @abstractmethod
    async def save(self, token: RefreshToken) -> None:
        raise NotImplementedError

    @abstractmethod
    async def find_by_token_hash(self, token_hash: str) -> RefreshToken | None:
        raise NotImplementedError

    @abstractmethod
    async def revoke(self, token_hash: str) -> None:
        raise NotImplementedError
