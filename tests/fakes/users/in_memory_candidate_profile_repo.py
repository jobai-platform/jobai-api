from uuid import UUID, uuid4

from app.application.users.candidate_profile_ports import CandidateProfileRepository
from app.domain.users.candidate_profile import CandidateProfile


class InMemoryCandidateProfileRepository(CandidateProfileRepository):
    def __init__(self) -> None:
        self._by_user_id: dict[str, CandidateProfile] = {}

    async def get_by_user_id(self, user_id: UUID) -> CandidateProfile | None:
        return self._by_user_id.get(str(user_id))

    async def save(self, profile: CandidateProfile) -> CandidateProfile:
        if profile.id is None:
            profile.id = uuid4()
        self._by_user_id[str(profile.user_id)] = profile
        return profile
