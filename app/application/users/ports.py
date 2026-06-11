from abc import ABC, abstractmethod
from collections.abc import Sequence
from datetime import datetime
from uuid import UUID

from app.domain.common.deletion import DeletionInfo
from app.domain.users.entities import Candidate
from app.domain.users.value_objects import Email


class UserRepository(ABC):
    """
    Abstract base class that represents a user repository.
    """
    @abstractmethod
    async def get_by_id(self, user_id: UUID) -> Candidate | None:
        """
        Get user by id.
        :param user_id: User id.
        :return: User object.
        """
        raise NotImplementedError()

    @abstractmethod
    async def get_by_email(self, email: Email) -> Candidate | None:
        """
        Get user by email.
        :param email: User email.
        :return: User object.
        """
        raise NotImplementedError()

    @abstractmethod
    async def list_all(
        self,
        skip: int | None = 0,
        limit: int | None = 50,
        sort_by: str | None = None,
        ascending: bool | None = True,
    ) -> Sequence[Candidate]:
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
    async def create(self, user: Candidate) -> Candidate:
        """
        Create new user.
        :param user: Candidate object.
        :return: User object.
        """
        raise NotImplementedError()

    @abstractmethod
    async def update(self, user_id: UUID, user: Candidate) -> Candidate | None:
        """
        Update user.
        :param user_id: User id.
        :param user: Candidate object.
        :return: User object.
        """
        raise NotImplementedError()

    @abstractmethod
    async def delete(self, user_id: UUID) -> None:
        """ Delete user by id. """
        raise NotImplementedError()

    @abstractmethod
    async def soft_delete(self, user_id: UUID, deletion: DeletionInfo) -> None:
        """Mark user as soft-deleted by setting deletion info."""
        raise NotImplementedError()

    @abstractmethod
    async def restore(self, user_id: UUID) -> None:
        """Restore a soft-deleted user (clear deletion info)."""
        raise NotImplementedError()

    @abstractmethod
    async def purge_older_than(self, cutoff: datetime) -> int:
        """Permanently delete rows soft-deleted at or before cutoff. Returns count."""
        raise NotImplementedError()

    @abstractmethod
    async def find_by_linkedin_id(self, linkedin_id: str) -> Candidate | None:
        """Return the user whose linkedin_id matches, or None."""
        raise NotImplementedError()

    @abstractmethod
    async def update_stripe_customer_id(self, user_id: UUID, stripe_customer_id: str | None) -> None:
        """Update the stripe customer ID for a user."""
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
