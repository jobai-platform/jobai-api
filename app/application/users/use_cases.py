from collections.abc import Sequence
from datetime import datetime
from uuid import UUID

from app.application.users.candidate_profile_ports import CandidateProfileRepository
from app.application.users.ports import PasswordHasher, UserRepository
from app.domain.common.exceptions import BadRequestError, ConflictError, NotFoundError
from app.domain.users.candidate_profile import CandidateProfile
from app.domain.users.entities import Candidate
from app.domain.users.value_objects import Email, HashedPassword


class CandidateService:
    """
    Application service (Use Cases) for Users Entity.
    - Orchestrates user-related operations.
    - Raises domain-friendly AppErrors exceptions for consistent HTTP mapping
      in Presentation layer (FastAPI exceptions handlers).
    """
    def __init__(
        self,
        user_repo: UserRepository,
        pwd_hasher: PasswordHasher,
        profile_repo: CandidateProfileRepository | None = None,
    ):
        self.repo = user_repo
        self.pwd_hasher = pwd_hasher
        self._profile_repo = profile_repo


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
        role: str | None = "user",
        is_active: bool | None = True,
    ) -> Candidate:
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

        hashed_raw = self.pwd_hasher.hash_password(password) if password else None
        hashed_pw = HashedPassword(hashed_raw) if hashed_raw else None

        user = Candidate(
            id=None,
            email=email_vo,
            username=username,
            first_name=first_name,
            last_name=last_name,
            hashed_password=hashed_pw,
            role=role,
            is_active=is_active,
        )

        created = await self.repo.create(user)

        if self._profile_repo is not None:
            await self._profile_repo.save(CandidateProfile(user_id=created.id))

        return created

    async def list_users(
        self,
        skip: int = 0,
        limit: int = 50,
        sort_by: str | None = None,
        ascending: bool | None = None,
    ) -> Sequence[Candidate]:
        """
        List users with pagination.
        :param skip: Number of records to skip for pagination.
        :param limit: Maximum number of users to return.
        :param sort_by: Field to sort by.
        :param ascending: Sort by ascending.
        :return: Collection of users.
        """
        all_users = await self.repo.list_all(
            skip=skip, limit=limit, sort_by=sort_by, ascending=ascending
        )
        visible = [u for u in all_users if not getattr(u, "deletion", None) or not u.deletion.is_deleted]  # noqa: E501
        return visible

    async def get_user_by_id(self, user_id: UUID) -> Candidate | None:
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
        partial_candidate: Candidate,
    ) -> Candidate | None:
        """
        Update an existing user.
        :param user_id: User ID.
        :param partial_user: Partial user.
        :return: User object.
        """
        updated = await self.repo.update(user_id, partial_candidate)
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


UserService = CandidateService
