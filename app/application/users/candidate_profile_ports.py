from abc import ABC, abstractmethod
from uuid import UUID

from app.domain.users.candidate_profile import CandidateProfile


class CandidateProfileRepository(ABC):

    @abstractmethod
    async def get_by_user_id(self, user_id: UUID) -> CandidateProfile | None: ...

    @abstractmethod
    async def save(self, profile: CandidateProfile) -> CandidateProfile: ...
