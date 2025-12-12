from uuid import UUID, uuid4
from typing import Optional, Sequence

from app.application.users.ports import UserRepository
from app.domain.users.entities import User
from app.domain.users.value_objects import Email


class InMemoryUserRepository(UserRepository):
    """
    Fake repository for tests.
    Implements the full UserRepository port (ABC), so it can be used in any
    application-layer test without breaking instantiation.
    """
    def __init__(self) -> None:
        self._users_by_id: dict[str, User] = {}
        self._users_by_email: dict[str, User] = {}

    async def get_by_id(self, user_id: UUID) -> Optional[User]:
        return self._users_by_id.get(str(user_id))

    async def get_by_email(self, email: Email) -> Optional[User]:
        return self._users_by_email.get(email.value)

    async def list_all(
        self,
        skip: int = 0,
        limit: int = 50,
        sort_by: str | None = None,
        ascending: bool | None = True,
    ) -> Sequence[User]:
        # Deterministic order for tests
        users = list(self._users_by_id.values())

        # Optional sorting (only if attribute exists on User)
        if sort_by and hasattr(User, sort_by):
            users.sort(key=lambda u: getattr(u, sort_by) or "")
            if ascending is False:
                users.reverse()

        return users[skip : skip + limit]

    async def count(self) -> int:
        return len(self._users_by_id)

    async def create(self, user: User) -> User:
        new_id = uuid4()

        created = User(
            id=new_id,
            email=user.email,
            username=user.username,
            first_name=user.first_name,
            last_name=user.last_name,
            hashed_password=user.hashed_password,
            role=user.role,
            is_active=user.is_active,
            stripe_customer_id=user.stripe_customer_id,
            created_at=user.created_at,
            updated_at=user.updated_at,
        )

        self._users_by_id[str(new_id)] = created
        self._users_by_email[created.email.value] = created
        return created

    async def update(self, user_id: UUID, user: User) -> Optional[User]:
        key = str(user_id)
        existing = self._users_by_id.get(key)
        if not existing:
            return None

        # Partial update semantics: keep existing values if incoming are None
        updated = User(
            id=existing.id,
            email=user.email or existing.email,
            username=user.username if user.username is not None else existing.username,
            first_name=user.first_name if user.first_name is not None else existing.first_name,
            last_name=user.last_name if user.last_name is not None else existing.last_name,
            hashed_password=user.hashed_password if user.hashed_password is not None else existing.hashed_password,
            role=user.role or existing.role,
            is_active=user.is_active if user.is_active is not None else existing.is_active,
            stripe_customer_id=user.stripe_customer_id if user.stripe_customer_id is not None else existing.stripe_customer_id,
            created_at=existing.created_at,
            updated_at=user.updated_at or existing.updated_at,
        )

        self._users_by_id[key] = updated
        self._users_by_email[updated.email.value] = updated
        return updated

    async def delete(self, user_id: UUID) -> None:
        key = str(user_id)
        user = self._users_by_id.pop(key, None)
        if user:
            self._users_by_email.pop(user.email.value, None)
