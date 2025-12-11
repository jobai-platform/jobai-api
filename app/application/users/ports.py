from uuid import UUID
from abc import ABC, abstractmethod
from typing import Optional, Sequence

from app.domain.users.entities import User


class UserRepository(ABC):
    """
    Abstract base class that represents a user repository.
    """

    @abstractmethod
    async def get_by_id(self, user_id: UUID) -> Optional[User]:
        """
        Get user by id.
        :param user_id: User id.
        :return: User object.
        """
        raise NotImplementedError()

    @abstractmethod
    async def get_by_email(self, email: str) -> Optional[User]:
        """
        Get user by email.
        :param email: User email.
        :return: User object.
        """
        raise NotImplementedError()

    @abstractmethod
    async def list_all(
        self,
        skip: Optional[int] = 0,
        limit: Optional[int] = 50,
        sort_by: Optional[str] = None,
        ascending: Optional[bool] = True,
    ) -> Sequence[User]:
        """
        List all users.
        :return: List of users.
        """
        raise NotImplementedError()

    @abstractmethod
    async def count(self) -> int:
        """
        Count number of users.
        :return: Number of users.
        """
        raise NotImplementedError()

    @abstractmethod
    async def create(self, user: User) -> User:
        """
        Create new user.
        :param user: User object.
        :return: User object.
        """
        raise NotImplementedError()

    @abstractmethod
    async def update(self, user_id: UUID, user: User) -> Optional[User]:
        """
        Update user.
        :param user_id: User id.
        :param user: User object.
        :return: User object.
        """
        raise NotImplementedError()

    @abstractmethod
    async def delete(self, user_id: UUID) -> None:
        """ Delete user by id. """
        raise NotImplementedError()


class PasswordHasher(ABC):
    """Port pour le hash de mot de passe (adapter : PasswordService)."""

    @abstractmethod
    def hash_password(self, raw_password: str) -> str:
        raise NotImplementedError

    @abstractmethod
    def verify(self, raw_password: str, hashed_password: str) -> bool:
        """Verify a raw password against a hashed password."""
        raise NotImplementedError
