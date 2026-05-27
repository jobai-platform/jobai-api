from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from uuid import UUID

from app.domain.common.deletion import DeletionInfo
from app.domain.common.exceptions import ConflictError
from app.domain.users.value_objects import Email, HashedPassword, LinkedInProfile


class CandidateRole(str, Enum):
    USER = "user"
    ADMIN = "admin"


@dataclass(slots=True)
class Candidate:
    id: UUID
    email: Email
    username: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    hashed_password: HashedPassword | None = None
    role: CandidateRole | None = CandidateRole.USER
    is_active: bool = True
    linkedin_id: str | None = None
    avatar_url: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    deletion: DeletionInfo = field(default_factory=DeletionInfo)

    def attach_linkedin(self, profile: LinkedInProfile) -> None:
        if self.linkedin_id is not None and self.linkedin_id != profile.linkedin_id:
            raise ConflictError(
                code="linkedin_already_attached",
                details=(
                    f"Candidate already linked to a different LinkedIn account ({self.linkedin_id})"
                ),
            )
        self.linkedin_id = profile.linkedin_id
        self.avatar_url = profile.avatar_url
