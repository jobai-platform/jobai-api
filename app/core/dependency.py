from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.users.ports import UserRepository
from app.application.users.use_cases import UserService
from app.infrastructure.config.database import get_async_session
from app.infrastructure.persistence.repositories.user_sqlalchemy import SqlAlchemyUserRepository
from app.infrastructure.security.password_service import PasswordServiceAdapter


DbSession = Annotated[AsyncSession, Depends(get_async_session)]


def get_user_repository(
    session: DbSession,
) -> UserRepository:
    """FastAPI dependency that provides a UserRepository instance."""
    return SqlAlchemyUserRepository(session=session)


def get_user_service(
    repo: UserRepository = Depends(get_user_repository),
) -> UserService:
    """FastAPI dependency that provides a UserService instance."""
    pwd_hasher = PasswordServiceAdapter()
    return UserService(user_repo=repo, pwd_hasher=pwd_hasher)
