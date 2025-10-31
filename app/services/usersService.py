from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.interfaces.interface_UserRepository import UserRepositoryInterface
from app.schemas.UserSchemas import UserCreate, UserRead, UserUpdate
from app.utils.jwt_service import PasswordService, JWTService


class UserService:
    """Service class for user-related operations."""

    def __init__(
        self,
        repo: UserRepositoryInterface,
        pwd: PasswordService | None = None,
        jwt: JWTService | None = None
    ):
        self.repo = repo
        self.pwd = pwd or PasswordService()
        self.jwt = jwt or JWTService()


    async def register(
        self,
        session: AsyncSession,
        data: UserCreate
    ) -> UserRead:
        """
        Register a new user after checking if the email is already in use.
        Raises ValueError if the email is already registered.
        :raises ValueError: If the email is already registered.
        :param session: AsyncSession
        :param data: UserCreate
        :return: UserRead
        """
        existing = await self.repo.get_by_email(session, data.email)
        if existing:
            raise ValueError("Email already registered")
        pwd_hash = self.pwd.hash_password(data.password) if data.password else None
        user = await self.repo.create(session, data, hashed_password=pwd_hash)

        return user


    async def list(
        self,
        session: AsyncSession,
        skip: int = 0,
        limit: int = 50,
    ) -> list[UserRead]:
        """
        List users with pagination.
        :param session: AsyncSession
        :param skip: Number of records to skip for pagination.
        :param limit: Maximum number of records to return.
        :return: List of UserRead
        """
        return list(await self.repo.list(session, skip=skip, limit=limit))


    async def get(
        self,
        session: AsyncSession,
        id_: UUID
    ) -> UserRead | None:
        """
        Retrieve a user by their ID.
        :param session: AsyncSession
        :param id_: User ID
        :return: UserRead or None if not found
        """
        return await self.repo.get(session, id_)


    async def count(
        self,
        session: AsyncSession
    ) -> int:
        """
        Count total number of users.
        :param session: AsyncSession
        :return: Total user count
        """
        return await self.repo.count(session)


    async def update(
        self,
        session: AsyncSession,
        id_: UUID,
        data: UserUpdate
    ) -> UserRead | None:
        """
        Update an existing user.
        :param session: AsyncSession
        :param id_: User ID
        :param data: UserUpdate
        :return: Updated UserRead or None if user not found
        """
        return await self.repo.update(session, id_, data)


    async def delete(
        self,
        session: AsyncSession,
        id_: UUID
    ) -> None:
        """
        Delete a user by their ID.
        :param session: AsyncSession
        :param id_: User ID
        :return: True if deletion was successful, False otherwise
        """
        return await self.repo.delete(session, id_)
