from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID

from app.domain.common.deletion import DeletionInfo
from app.domain.users.value_objects import Email, LinkedInProfile


@dataclass(slots=True)
class User:
    id: UUID | None
    email: Email
    username: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    hashed_password: str | None = None
    role: str = "user"
    is_active: bool = True
    stripe_customer_id: str | None = None
    linkedin_id: str | None = None
    avatar_url: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    deletion: DeletionInfo = field(default_factory=DeletionInfo)

    def attach_linkedin(self, profile: "LinkedInProfile") -> None:
        """
        Attach a LinkedIn identity to this user.
        Raises ValueError if a different linkedin_id is already attached
        (prevents account hijacking via email collision + linkedin swap).
        """
        if self.linkedin_id is not None and self.linkedin_id != profile.linkedin_id:
            msg = f"User already linked to a different LinkedIn account ({self.linkedin_id})"
            raise ValueError(msg)
        self.linkedin_id = profile.linkedin_id
        self.avatar_url = profile.avatar_url
