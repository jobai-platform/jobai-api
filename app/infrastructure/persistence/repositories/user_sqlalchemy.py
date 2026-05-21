from typing import Optional, Sequence
from datetime import datetime

from uuid import UUID
from sqlalchemy import select, update, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.users.ports import UserRepository
from app.domain.users.entities import Candidate
from app.domain.users.value_objects import Email, HashedPassword
from app.infrastructure.persistence.models.user import UserModel
from app.domain.common.deletion import DeletionInfo


def _to_domain(row: UserModel) -> Candidate:
    deletion = DeletionInfo(
        is_deleted=bool(getattr(row, "is_deleted", False)),
        deleted_at=getattr(row, "deleted_at", None),
        scheduled_purge_at=getattr(row, "scheduled_purge_at", None),
    )
    hp = row.hashed_password
    return Candidate(
        id=row.id,
        email=Email.from_raw(row.email),
        username=row.username,
        first_name=row.first_name,
        last_name=row.last_name,
        hashed_password=HashedPassword(hp) if hp else None,
        role=row.role,
        is_active=row.is_active,
        linkedin_id=getattr(row, "linkedin_id", None),
        avatar_url=getattr(row, "avatar_url", None),
        created_at=row.created_at,
        updated_at=row.updated_at,
        deletion=deletion,
    )


class SqlAlchemyUserRepository(UserRepository):
    """
    SQLAlchemy Adapter for Users
    """
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_email(self, email: str | Email) -> Optional[Candidate]:
        """
        Retrieve user by their email.
        :param email: User email.
        :return: User object.
        """
        email_str = str(email) if isinstance(email, Email) else str(email).strip().lower()

        result = await self.session.execute(
            select(UserModel).where(UserModel.email == email_str)
        )
        row = result.scalars().one_or_none()
        return _to_domain(row) if row else None

    async def get_by_id(self, user_id: UUID) -> Optional[Candidate]:
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
    ) -> Sequence[Candidate]:
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

    async def create(self, user: Candidate) -> Candidate:
        """
        Create a new user.
        :param user: User object.
        :return: User object.
        """
        # Accept Email VO or raw string (or None)
        if getattr(user, "email", None) is not None:
            if isinstance(user.email, Email):
                email_val = user.email.value
            else:
                email_val = str(user.email).strip().lower() if user.email else None
        else:
            email_val = None

        new_user = UserModel(
            email=email_val,
            username=user.username,
            first_name=user.first_name,
            last_name=user.last_name,
            hashed_password=user.hashed_password.value if user.hashed_password else None,
            role=user.role,
            is_active=user.is_active,
            linkedin_id=user.linkedin_id,
            avatar_url=user.avatar_url,
        )

        self.session.add(new_user)
        await self.session.commit()
        await self.session.refresh(new_user)
        return _to_domain(new_user)

    async def update(self, user_id: UUID, user: Candidate) -> Optional[Candidate]:
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

        # Safely extract email string if present
        email_value = None
        if getattr(user, "email", None) is not None:
            if isinstance(user.email, Email):
                email_value = user.email.value
            else:
                email_value = str(user.email).strip().lower() if user.email else None

        values = {
            "email": email_value or existing_row.email,
            "username": user.username or existing_row.username,
            "first_name": user.first_name or existing_row.first_name,
            "last_name": user.last_name or existing_row.last_name,
            "hashed_password": (user.hashed_password.value if user.hashed_password else None) or existing_row.hashed_password,
            "role": user.role or existing_row.role,
            "is_active": user.is_active if user.is_active is not None else existing_row.is_active,
            "linkedin_id": user.linkedin_id if user.linkedin_id is not None else existing_row.linkedin_id,
            "avatar_url": user.avatar_url if user.avatar_url is not None else existing_row.avatar_url,
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

    async def soft_delete(self, user_id: UUID, deletion: object) -> None:
        """Mark the user as soft-deleted by setting is_deleted/deleted_at/scheduled_purge_at."""
        # Accept either DeletionInfo VO or a simple object with attributes
        deleted_at = getattr(deletion, "deleted_at", None)
        scheduled = getattr(deletion, "scheduled_purge_at", None)

        await self.session.execute(
            update(UserModel)
            .where(UserModel.id == user_id)
            .values(is_deleted=True, deleted_at=deleted_at, scheduled_purge_at=scheduled)
        )
        await self.session.commit()

    async def restore(self, user_id: UUID) -> None:
        await self.session.execute(
            update(UserModel)
            .where(UserModel.id == user_id)
            .values(is_deleted=False, deleted_at=None, scheduled_purge_at=None)
        )
        await self.session.commit()

    async def purge_older_than(self, cutoff: datetime) -> int:
        """Permanently delete rows that are soft-deleted and older than cutoff; return count."""
        # Use DELETE ... RETURNING to get count when supported
        stmt = select(UserModel).where(UserModel.is_deleted == True, UserModel.deleted_at <= cutoff)
        result = await self.session.execute(stmt)
        rows = result.scalars().all()
        count = 0
        for row in rows:
            await self.session.delete(row)
            count += 1
        if count:
            await self.session.commit()
        return count

    async def find_by_linkedin_id(self, linkedin_id: str) -> Optional[Candidate]:
        """Return the user with the given linkedin_id, or None."""
        result = await self.session.execute(
            select(UserModel).where(UserModel.linkedin_id == linkedin_id)
        )
        row = result.scalars().one_or_none()
        return _to_domain(row) if row else None

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
