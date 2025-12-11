from abc import ABC, abstractmethod
from typing import Optional, Mapping


class TokenService(ABC):
    """ Abstract class to implement JWT and Token authentication """

    @abstractmethod
    def create_access_token(
        self,
        subject: str,
        extra: Optional[Mapping[str, any]] = None,
    ) -> str:
        raise NotImplementedError()

    @abstractmethod
    def create_refresh_token(
        self,
        subject: str,
        extra: Optional[Mapping[str, any]] = None,
    ) -> str:
        raise NotImplementedError()

    @abstractmethod
    def decode_token(
        self,
        token: str,
    ) -> Mapping[str, any]:
        raise NotImplementedError()
