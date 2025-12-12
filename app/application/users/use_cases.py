from typing import Optional, Sequence
from uuid import UUID

from app.application.users.ports import UserRepository, PasswordHasher
from app.domain.users.entities import User
from app.domain.users.value_objects import Email


class UserService:
    def __init__(self, user_repo: UserRepository, pwd_hasher: PasswordHasher):
        self.repo = user_repo
        self.pwd_hasher = pwd_hasher

    async def register(
        self,
        email: str,
        password: str | None,
        username: str | None = None,
        first_name: str | None = None,
        last_name: str | None = None,
        stripe_customer_id: str | None = None,
    ) -> User:
        """
        Registers a new user.
        :param email: Email address of the user.
        :param password: .
        :param username: Username associated with the user.
        :param first_name: First name of the user.
        :param last_name: Last name of the user.
        :param stripe_customer_id: Stripe customer ID.
        :return: User object.
        """
        email_vo = Email.from_raw(email)

        existing_user = await self.repo.get_by_email(email_vo)
        if existing_user:
            raise ValueError(f"User with email {email_vo.value} already exists")

        hashed = self.pwd_hasher.hash_password(password) if password else None

        user = User(
            id = None,
            email = email_vo,
            username = username,
            first_name = first_name,
            last_name = last_name,
            hashed_password = hashed,
            role="user",
            is_active = True,
            stripe_customer_id = stripe_customer_id,
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
        return await self.repo.list_all(skip=skip, limit=limit, sort_by=sort_by, ascending=ascending)

    async def get_user_by_id(self, user_id: UUID) -> Optional[User]:
        """
        Get user by ID.
        :param user_id: User ID.
        :return: User object.
        """
        return await self.repo.get_by_id(user_id)

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
        Update existing user.
        :param user_id: User ID.
        :param partial_user: Partial user.
        :return: User object.
        """
        return await self.repo.update(user_id, partial_user)

    async def delete_user(self, user_id: UUID) -> None:
        return await self.repo.delete(user_id)
