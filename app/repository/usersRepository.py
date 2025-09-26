from typing import Optional, Sequence
from uuid import UUID

from sqlalchemy import select, update, delete, asc, desc, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.UserSchemas import UserRead, UserRoles, UserCreate, UserUpdate
from app.interfaces.interface_UserRepository import UserRepositoryInterface
from app.models.usersModels import Users as UsersORM, Users


def _to_read(row: UsersORM) -> UserRead:
    return UserRead(
        id=row.id,
        email=row.email,
        username=row.username,
        first_name=row.first_name,
        last_name=row.last_name,
        role=UserRoles(row.role),
        is_active=row.is_active,
    )

class UserRepository(UserRepositoryInterface):
    """Repository for user-related database operations."""

    async def get_by_email(self, session: AsyncSession, email: str) -> Optional[UserRead]:
        """Retrieve a user by their email."""
        row = (await session.execute(select(UsersORM).where(UsersORM.email == email))).scalars().one_or_none()
        return _to_read(row) if row else None


    async def get(self, session: AsyncSession, id_: UUID) -> Optional[UserRead]:
        """Retrieve a user by their ID."""
        result = await session.execute(
            select(UsersORM).where(UsersORM.id == id_)
        )
        row = result.scalars_one_or_none()
        return _to_read(row) if row else None


    async def list(
        self,
        session: AsyncSession,
        skip: int = 0,
        limit: int = 50,
        sort_by: str | None = None,
        ascending: bool = True,
    ) -> Sequence[UserRead]:
        """List users with pagination."""
        stmt = select(UsersORM).offset(skip).limit(limit)

        if sort_by and hasattr(UsersORM, sort_by):
            column = getattr(UsersORM, sort_by)
            stmt = stmt.order_by(column.asc() if ascending else column.desc())

        rows = (await session.execute(stmt)).scalars().all()
        return [_to_read(row) for row in rows]


    async def count(self, session: AsyncSession) -> int:
        """Count total number of users."""
        result = await session.execute(select(func.count()).select_from(UsersORM.id))
        return int(result.scalar_one())


    async def create(self, session: AsyncSession, data: UserCreate) -> UserRead:
        """Create a new user."""
        new_user = UsersORM(
            email=data.email,
            username=data.username,
            first_name=data.first_name,
            last_name=data.last_name,
            avatar=data.avatar,
            role=UserRoles.USER.value,
            is_active=True,
            stripe_customer_id=data.stripe_customer_id,
        )
        if data.password:
            new_user.set_password(data.password)

        session.add(new_user)
        await session.commit()
        await session.refresh(new_user)
        return _to_read(new_user)


    async def update(self, session: AsyncSession, id_: UUID, data: UserUpdate) -> Optional[UserRead]:
        """Update an existing user."""
        values = data.model_dump(exclude_unset=True)

        if values:
            await session.execute(
                update(UsersORM).where(UsersORM.id == id_).values(**values)
            )
            await session.commit()

        orm = (await session.execute(select(UsersORM).where(UsersORM.id == id_))).scalars().one_or_none()
        return _to_read(orm) if orm else None


    async def delete(self, session: AsyncSession, id_: UUID) -> None:
        """Delete a user by their ID."""
        result = await session.execute(select(UsersORM).where(UsersORM.id == id_))
        user = result.scalars().first()
        if user:
            await session.delete(user)
            await session.commit()
