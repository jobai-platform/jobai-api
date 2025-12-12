from abc import ABC
from typing import Optional, Sequence

from uuid import UUID
from sqlalchemy import select, update, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.users.ports import UserRepository
from app.domain.users.entities import User
from app.domain.users.value_objects import Email
from app.infrastructure.persistence.models.user import UserModel


def _to_domain(row: UserModel) -> User:
    """
    Mapping ORM to Domain
    :param row: User Model
    :return: User Object.
    """
    return User(
        id=row.id,
        email=Email.from_raw(row.email),
        username=row.username,
        first_name=row.first_name,
        last_name=row.last_name,
        hashed_password=row.hashed_password,
        role=row.role,
        is_active=row.is_active,
        is_superuser=row.is_superuser,
        stripe_customer_id=row.stripe_customer_id,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


class SqlAlchemyUserRepository(UserRepository):
    """
    SQLAlchemy Adapter for Users
    """
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_email(self, email: Email) -> Optional[User]:
        """
        Retrieve user by their email.
        :param email: User email.
        :return: User object.
        """
        result = await self.session.execute(
            select(UserModel).where(UserModel.email == email)
        )
        row = result.scalars().one_or_none()
        return _to_domain(row) if row else None

    async def get_by_id(self, user_id: UUID) -> Optional[User]:
        """
        Retrieve user by their ID.
        :param user_id: User ID.
        :return: User object.
        """
        result = await self.session.execute(
            select(UserModel).where(UserModel.id == user_id)
        )
        row = result.scalars().one_or_none()
        return _to_domain(row) if row else None

    async def list_all(
        self,
        skip: int = 0,
        limit: int = 50,
        sort_by: str | None = None,
        ascending: bool = True,
    ) -> Sequence[User]:
        """
        List all users.
        :param skip: Number of items to skip.
        :param limit: Number of items to return.
        :param sort_by: Column name.
        :param ascending: Whether to sort ascending or descending.
        :return: List of users.
        """
        stmt = select(UserModel).offset(skip).limit(limit)

        if sort_by and hasattr(UserModel, sort_by):
            column = getattr(UserModel, sort_by)
            stmt = stmt.order_by(column.asc() if ascending else column.desc())

        result = await self.session.execute(stmt)
        rows = result.scalars().all()
        return [_to_domain(row) for row in rows]

    async def create(self, user: User) -> User:
        """
        Create a new user.
        :param user: User object.
        :return: User object.
        """
        new_user = UserModel(
            email=user.email.value,
            username=user.username,
            first_name=user.first_name,
            last_name=user.last_name,
            hashed_password=user.hashed_password,
            role=user.role,
            is_active=user.is_active,
            is_superuser=user.is_superuser,
            stripe_customer_id=user.stripe_customer_id,
        )

        self.session.add(new_user)
        await self.session.commit()
        await self.session.refresh(new_user)
        return _to_domain(new_user)

    async def update(self, user_id: UUID, user: User) -> Optional[User]:
        """
        Update an existing user.
        :param user_id: User ID.
        :param user: User object.
        :return: User object.
        """
        result = await self.session.execute(
            select(UserModel).where(UserModel.id == user_id)
        )
        existing_row = result.scalars().one_or_none()
        if not existing_row:
            return None

        values = {
            "email": user.email.value or existing_row.email,
            "username": user.username or existing_row.username,
            "first_name": user.first_name or existing_row.first_name,
            "last_name": user.last_name or existing_row.last_name,
            "hashed_password": user.hashed_password or existing_row.hashed_password,
            "role": user.role or existing_row.role,
            "is_active": user.is_active if user.is_active is not None else existing_row.is_active,
            "is_superuser": user.is_superuser if user.is_superuser is not None else existing_row.is_superuser,
            "stripe_customer_id": user.stripe_customer_id or existing_row.stripe_customer_id,
        }

        await self.session.execute(
            update(UserModel)
            .where(UserModel.id == user_id)
            .values(**values)
        )
        await self.session.commit()

        result = await self.session.execute(
            select(UserModel).where(UserModel.id == user_id)
        )
        orm = result.scalars().one_or_none()
        return _to_domain(orm) if orm else None

    async def delete(self, user_id: UUID) -> None:
        """
        Delete an existing user.
        :param user_id: User ID.
        :return: None
        """
        result = await self.session.execute(
            select(UserModel).where(UserModel.id == user_id)
        )
        user = result.scalars().first()
        if user:
            await self.session.delete(user)
            await self.session.commit()

    async def count(self) -> int:
        """
        Return total number of users.
        :return: int
        """
        result = await self.session.execute(
            select(func.count()).select_from(UserModel)
        )
        total = result.scalar_one()
        return int(total)
