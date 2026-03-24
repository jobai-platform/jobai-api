from typing import Optional, Sequence
from uuid import UUID
from datetime import datetime

from app.application.users.ports import UserRepository, PasswordHasher
from app.domain.common.exceptions import ConflictError, BadRequestError, NotFoundError
from app.domain.users.entities import User
from app.domain.users.value_objects import Email


class UserService:
    """
    Application service (Use Cases) for Users Entity.
    - Orchestrates user-related operations.
    - Raises domain-friendly AppErrors exceptions for consistent HTTP mapping
      in Presentation layer (FastAPI exceptions handlers).
    """
    def __init__(self, user_repo: UserRepository, pwd_hasher: PasswordHasher):
        self.repo = user_repo
        self.pwd_hasher = pwd_hasher


    def _to_email_vo(self, email: str | Email) -> Email:
        """
        Converts a raw email string or Email value object to an Email value object.
        :param email: email as str or Email VO.
        :return: Email value object.
        """
        if isinstance(email, Email):
            return email
        return Email.from_raw(email)


    async def register(
        self,
        *,
        email: str | Email,
        password: str | None,
        username: str | None = None,
        first_name: str | None = None,
        last_name: str | None = None,
        stripe_customer_id: str | None = None,
        role: str | None = "user",
        is_active: bool | None = True,
    ) -> User:
        """
        Registers a new user.
        :param email: Email address of the user.
        :param password: .
        :param username: Username associated with the user.
        :param first_name: First name of the user.
        :param last_name: Last name of the user.
        :param stripe_customer_id: Stripe customer ID.
        :param role: Role of the user.
        :param is_active: Whether the user is active.
        :return: User object.
        """
        email_vo = self._to_email_vo(email)

        if password is not None and len(password) < 8:
            raise BadRequestError(
                code="invalid_user_input",
                details="Password must be at least 8 characters",
            )

        existing_user = await self.repo.get_by_email(email_vo)
        if existing_user:
            raise ConflictError(
                code="user_already_exists",
                details="Email already exists.",
            )

        hashed = self.pwd_hasher.hash_password(password) if password else None

        user = User(
            id = None,
            email = email_vo,
            username = username,
            first_name = first_name,
            last_name = last_name,
            hashed_password = hashed,
            stripe_customer_id = stripe_customer_id,
            role= role,
            is_active = is_active,
        )

        return await self.repo.create(user)

    async def list_users(
        self,
        skip: int = 0,
        limit: int = 50,
        sort_by: str | None = None,
        ascending: bool | None = None,
    ) -> Sequence[User]:
        """
        List users with pagination.
        :param skip: Number of records to skip for pagination.
        :param limit: Maximum number of users to return.
        :param sort_by: Field to sort by.
        :param ascending: Sort by ascending.
        :return: Collection of users.
        """
        all_users = await self.repo.list_all(skip=skip, limit=limit, sort_by=sort_by, ascending=ascending)
        # Exclude soft-deleted users by default
        visible = [u for u in all_users if not getattr(u, "deletion", None) or not u.deletion.is_deleted]
        return visible

    async def get_user_by_id(self, user_id: UUID) -> Optional[User]:
        """
        Get user by ID.
        :param user_id: User ID.
        :return: User object.
        """
        user = await self.repo.get_by_id(user_id)
        if not user:
            return None
        if getattr(user, "deletion", None) and user.deletion.is_deleted:
            # treat soft-deleted users as not found for read operations
            return None
        return user

    async def count_users(self) -> int:
        """
        Count users.
        :return: Number of users.
        """
        return await self.repo.count()

    async def update_user(
        self,
        user_id: UUID,
        partial_user: User,
    ) -> Optional[User]:
        """
        Update an existing user.
        :param user_id: User ID.
        :param partial_user: Partial user.
        :return: User object.
        """
        updated = await self.repo.update(user_id, partial_user)
        if not updated:
            raise NotFoundError(
                code="user_not_found",
                details="User not found.",
            )
        return updated

    async def delete_user(self, user_id: UUID) -> None:
        """
        Delete a user by ID.
        :param user_id: User ID.
        :return: None.
        """
        existing_user = await self.repo.get_by_id(user_id)
        if not existing_user:
            raise NotFoundError(
                code="user_not_found",
                details="User not found.",
            )
        # perform soft-delete via domain service
        from app.domain.common.domain_services import SoftDeleteService
        service = SoftDeleteService()
        deletion = service.mark_deleted(existing_user)

        await self.repo.soft_delete(user_id, deletion)
        return None

    async def restore_user(self, user_id: UUID) -> None:
        """
        Restore a soft-deleted user by ID.
        :param user_id: User ID.
        :return: None.
        """
        existing_user = await self.repo.get_by_id(user_id)
        if not existing_user:
            raise NotFoundError(code="user_not_found", details="User not found.")
        # if not deleted, no-op
        if not existing_user.deletion.is_deleted:
            return None

        await self.repo.restore(user_id)
        return None

    async def purge_users_older_than(self, cutoff: datetime) -> int:
        """
        Permanently purge soft-deleted users older than cutoff.
        :param cutoff: Cutoff datetime.
        :return: Number of users deleted.
        """
        deleted_count = await self.repo.purge_older_than(cutoff)
        return deleted_count
