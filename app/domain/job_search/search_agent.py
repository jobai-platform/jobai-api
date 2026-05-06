from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import UUID


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(slots=True)
class SearchAgent:
    candidate_id: UUID
    keywords: str
    location: str
    id: UUID | None = None
    remote_only: bool = False
    date_posted_within_days: int = 7
    limit: int = 25
    easy_apply_only: bool | None = None
    is_active: bool = True
    last_run_at: datetime | None = None
    created_at: datetime = field(default_factory=_utcnow)
    updated_at: datetime = field(default_factory=_utcnow)

    def __post_init__(self) -> None:
        self._validate()

    def _validate(self) -> None:
        if not self.keywords or not self.keywords.strip():
            raise ValueError("keywords cannot be empty")
        if not self.location or not self.location.strip():
            raise ValueError("location cannot be empty")
        if not (1 <= self.limit <= 100):
            raise ValueError("limit must be between 1 and 100")
        if not (1 <= self.date_posted_within_days <= 30):
            raise ValueError("date_posted_within_days must be between 1 and 30")

    def update(
        self,
        keywords: str | None = None,
        location: str | None = None,
        remote_only: bool | None = None,
        date_posted_within_days: int | None = None,
        limit: int | None = None,
        easy_apply_only: bool | None = None,
    ) -> None:
        if keywords is not None:
            self.keywords = keywords
        if location is not None:
            self.location = location
        if remote_only is not None:
            self.remote_only = remote_only
        if date_posted_within_days is not None:
            self.date_posted_within_days = date_posted_within_days
        if limit is not None:
            self.limit = limit
        if easy_apply_only is not None:
            self.easy_apply_only = easy_apply_only
        self.updated_at = _utcnow()
        self._validate()

    def mark_ran(self) -> None:
        self.last_run_at = _utcnow()
        self.updated_at = _utcnow()
