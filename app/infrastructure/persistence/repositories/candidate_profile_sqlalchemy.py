from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.users.candidate_profile_ports import CandidateProfileRepository
from app.domain.users.candidate_profile import CandidateProfile, RemotePreference
from app.infrastructure.persistence.models.candidate_profile import CandidateProfileModel


class SQLAlchemyCandidateProfileRepository(CandidateProfileRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_user_id(self, user_id: UUID) -> CandidateProfile | None:
        result = await self._session.execute(
            select(CandidateProfileModel).where(CandidateProfileModel.user_id == user_id)
        )
        model = result.scalar_one_or_none()
        return _to_domain(model) if model else None

    async def save(self, profile: CandidateProfile) -> CandidateProfile:
        result = await self._session.execute(
            select(CandidateProfileModel).where(CandidateProfileModel.user_id == profile.user_id)
        )
        model = result.scalar_one_or_none()

        if model is None:
            model = CandidateProfileModel(
                id=profile.id or uuid4(),
                user_id=profile.user_id,
            )
            self._session.add(model)

        model.current_title = profile.current_title
        model.years_of_experience = profile.years_of_experience
        model.skills = profile.skills
        model.desired_salary_min = profile.desired_salary_min
        model.desired_salary_max = profile.desired_salary_max
        model.preferred_locations = profile.preferred_locations
        model.remote_preference = profile.remote_preference.value
        model.bio = profile.bio
        model.cv_url = profile.cv_url

        # Flush to send any new INSERT or UPDATE to the database
        await self._session.flush([model])
        # Refresh to get any server-side defaults (like timestamps) that were set by the database
        await self._session.refresh(model)
        return _to_domain(model)


def _to_domain(model: CandidateProfileModel) -> CandidateProfile:
    return CandidateProfile(
        id=model.id,
        user_id=model.user_id,
        current_title=model.current_title,
        years_of_experience=model.years_of_experience,
        skills=list(model.skills or []),
        desired_salary_min=model.desired_salary_min,
        desired_salary_max=model.desired_salary_max,
        preferred_locations=list(model.preferred_locations or []),
        remote_preference=RemotePreference(model.remote_preference),
        bio=model.bio,
        cv_url=model.cv_url,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )
