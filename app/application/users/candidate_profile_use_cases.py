from __future__ import annotations

import logging
from dataclasses import dataclass
from uuid import UUID

from app.application.users.candidate_profile_ports import CandidateProfileRepository
from app.domain.users.candidate_profile import CandidateProfile, RemotePreference

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class UpsertProfileCommand:
    user_id: UUID
    current_title: str | None = None
    years_of_experience: int | None = None
    skills: list[str] | None = None
    desired_salary_min: int | None = None
    desired_salary_max: int | None = None
    preferred_locations: list[str] | None = None
    remote_preference: RemotePreference | None = None
    bio: str | None = None
    cv_url: str | None = None


class UpsertCandidateProfileUseCase:
    def __init__(self, repo: CandidateProfileRepository) -> None:
        self._repo = repo

    async def execute(self, command: UpsertProfileCommand) -> CandidateProfile:
        logger.info("UpsertCandidateProfile: user_id=%s", command.user_id)
        profile = await self._repo.get_by_user_id(command.user_id)

        if profile is None:
            logger.info("UpsertCandidateProfile: creating new profile for user_id=%s", command.user_id)
            profile = CandidateProfile(user_id=command.user_id)

        profile.upsert(
            current_title=command.current_title,
            years_of_experience=command.years_of_experience,
            skills=command.skills,
            desired_salary_min=command.desired_salary_min,
            desired_salary_max=command.desired_salary_max,
            preferred_locations=command.preferred_locations,
            remote_preference=command.remote_preference,
            bio=command.bio,
            cv_url=command.cv_url,
        )

        saved = await self._repo.save(profile)
        logger.info(
            "UpsertCandidateProfile: saved profile_id=%s is_complete=%s",
            saved.id,
            saved.is_complete,
        )
        return saved


class GetCandidateProfileUseCase:
    def __init__(self, repo: CandidateProfileRepository) -> None:
        self._repo = repo

    async def execute(self, user_id: UUID) -> CandidateProfile:
        logger.info("GetCandidateProfile: user_id=%s", user_id)
        profile = await self._repo.get_by_user_id(user_id)

        if profile is None:
            logger.info("GetCandidateProfile: auto-creating empty profile for user_id=%s", user_id)
            profile = CandidateProfile(user_id=user_id)
            profile = await self._repo.save(profile)

        return profile
