from abc import ABC, abstractmethod
from collections.abc import Mapping
from typing import Optional

from app.domain.users.value_objects import LinkedInProfile


class OAuthGateway(ABC):
    """
    Port for exchanging an OAuth authorization code for a normalized user profile.
    Concrete implementations: LinkedInOAuthAdapter, GoogleOAuthAdapter, ...
    """

    @abstractmethod
    async def exchange_code(self, code: str, redirect_uri: str) -> LinkedInProfile:
        """
        Exchange an OAuth authorization code for a LinkedInProfile.
        Raises UnauthorizedError if the code is invalid or expired.
        """
        raise NotImplementedError

    @abstractmethod
    def build_authorization_url(self, redirect_uri: str, state: str) -> str:
        """
        Build the provider's authorization URL to redirect the user to.
        """
        raise NotImplementedError


class TokenService(ABC):
    """ Abstract class to implement JWT and Token authentication """

    @abstractmethod
    def create_access_token(
        self,
        subject: str,
        extra: Optional[Mapping[str, any]] = None,
    ) -> str:
        raise NotImplementedError

    @abstractmethod
    def create_refresh_token(
        self,
        subject: str,
        extra: Optional[Mapping[str, any]] = None,
    ) -> str:
        raise NotImplementedError

    @abstractmethod
    def decode_token(
        self,
        token: str,
    ) -> Mapping[str, any]:
        raise NotImplementedError
