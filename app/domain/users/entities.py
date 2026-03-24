from uuid import UUID
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from app.domain.users.value_objects import Email
from app.domain.common.deletion import DeletionInfo


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
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    # Deletion / soft-delete information
    deletion: DeletionInfo = DeletionInfo()
