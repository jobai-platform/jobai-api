from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional


@dataclass(frozen=True, slots=True)
class DeletionInfo:
    is_deleted: bool = False
    deleted_at: Optional[datetime] = None
    scheduled_purge_at: Optional[datetime] = None

    def __post_init__(self):
        # ensure timezone-aware datetime (UTC)
        if self.deleted_at is not None and self.deleted_at.tzinfo is None:
            raise ValueError("deleted_at must be timezone-aware")
        if self.deleted_at is not None and self.deleted_at > datetime.now(timezone.utc):
            raise ValueError("deleted_at cannot be in the future")

    def with_deleted(self, when: datetime, retention: timedelta) -> "DeletionInfo":
        if when.tzinfo is None:
            raise ValueError("deleted_at must be timezone-aware")
        scheduled = when + retention
        return DeletionInfo(is_deleted=True, deleted_at=when, scheduled_purge_at=scheduled)

    def cleared(self) -> "DeletionInfo":
        return DeletionInfo(is_deleted=False, deleted_at=None, scheduled_purge_at=None)
