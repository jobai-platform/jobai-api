from datetime import datetime, timedelta, timezone
from typing import Optional

from app.domain.common.deletion import DeletionInfo


class SoftDeleteService:
    def mark_deleted(self, entity, when: Optional[datetime] = None, retention: Optional[timedelta] = None):
        """Return a new entity (or modified shallow copy) with deletion info set.

        The domain layer should not depend on infrastructure; this service operates on
        domain entities and their DeletionInfo value object.
        """
        if when is None:
            when = datetime.now(timezone.utc)
        if when.tzinfo is None:
            raise ValueError("when must be timezone-aware")
        if retention is None:
            retention = timedelta(days=365)

        # Create new DeletionInfo and set on entity
        deletion = DeletionInfo(is_deleted=True, deleted_at=when, scheduled_purge_at=when + retention)

        # Prefer to return a new instance if entity is a dataclass; try copy
        try:
            from dataclasses import replace

            return replace(entity, deletion=deletion)
        except Exception:
            # fallback: mutate in place
            entity.deletion = deletion
            return entity

    def restore(self, entity):
        try:
            from dataclasses import replace

            return replace(entity, deletion=DeletionInfo())
        except Exception:
            entity.deletion = DeletionInfo()
            return entity

