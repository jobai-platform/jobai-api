from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from uuid import UUID

from app.domain.common.deletion import DeletionInfo
from app.domain.users.value_objects import Email, LinkedInProfile


@dataclass
class User:
    id: Optional[UUID]
    email: Email
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    hashed_password: Optional[str] = None
    role: str = "user"
    is_active: bool = True
    stripe_customer_id: Optional[str] = None
    linkedin_id: Optional[str] = None
    avatar_url: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
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
