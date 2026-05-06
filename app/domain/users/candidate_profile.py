from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from uuid import UUID


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class RemotePreference(str, Enum):
    REMOTE = "remote"
    HYBRID = "hybrid"
    ONSITE = "onsite"
    ANY = "any"


@dataclass(slots=True)
class CandidateProfile:
    user_id: UUID
    id: UUID | None = None
    current_title: str | None = None
    years_of_experience: int | None = None
    skills: list[str] = field(default_factory=list)
    desired_salary_min: int | None = None
    desired_salary_max: int | None = None
    preferred_locations: list[str] = field(default_factory=list)
    remote_preference: RemotePreference = RemotePreference.ANY
    bio: str | None = None
    cv_url: str | None = None
    created_at: datetime = field(default_factory=_utcnow)
    updated_at: datetime = field(default_factory=_utcnow)

    def __post_init__(self) -> None:
        self.skills = _normalize_skills(self.skills)
        self._validate()

    def _validate(self) -> None:
        if self.years_of_experience is not None and self.years_of_experience < 0:
            raise ValueError("years_of_experience cannot be negative")
        if (
            self.desired_salary_min is not None
            and self.desired_salary_max is not None
            and self.desired_salary_min > self.desired_salary_max
        ):
            raise ValueError("desired_salary_min cannot exceed desired_salary_max")

    @property
    def is_complete(self) -> bool:
        return bool(self.current_title) and len(self.skills) > 0

    def upsert(
        self,
        current_title: str | None = None,
        years_of_experience: int | None = None,
        skills: list[str] | None = None,
        desired_salary_min: int | None = None,
        desired_salary_max: int | None = None,
        preferred_locations: list[str] | None = None,
        remote_preference: RemotePreference | None = None,
        bio: str | None = None,
        cv_url: str | None = None,
    ) -> None:
        if current_title is not None:
            self.current_title = current_title
        if years_of_experience is not None:
            self.years_of_experience = years_of_experience
        if skills is not None:
            self.skills = _normalize_skills(skills)
        if desired_salary_min is not None:
            self.desired_salary_min = desired_salary_min
        if desired_salary_max is not None:
            self.desired_salary_max = desired_salary_max
        if preferred_locations is not None:
            self.preferred_locations = preferred_locations
        if remote_preference is not None:
            self.remote_preference = remote_preference
        if bio is not None:
            self.bio = bio
        if cv_url is not None:
            self.cv_url = cv_url
        self.updated_at = _utcnow()
        self._validate()


def _normalize_skills(skills: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for s in skills:
        normalized = s.strip().lower()
        if normalized and normalized not in seen:
            seen.add(normalized)
            result.append(normalized)
    return result
