from uuid import UUID

from app.application.ai_analysis.ports import AIAnalysisRepository
from app.domain.ai_analysis.entities import AIAnalysis


class InMemoryAIAnalysisRepository(AIAnalysisRepository):
    """In-memory repository for use in application-layer tests (JOB-40)."""

    def __init__(self) -> None:
        self._store: dict[UUID, AIAnalysis] = {}

    async def save(self, analysis: AIAnalysis) -> None:
        self._store[analysis.id] = analysis

    async def find_by_id(self, id: UUID) -> AIAnalysis | None:
        return self._store.get(id)

    async def find_by_candidate_and_job(
        self,
        candidate_id: UUID,
        job_posting_id: UUID,
    ) -> AIAnalysis | None:
        return next(
            (
                a
                for a in self._store.values()
                if a.candidate_id == candidate_id and a.job_posting_id == job_posting_id
            ),
            None,
        )

    async def find_by_candidate(
        self,
        candidate_id: UUID,
        limit: int = 20,
    ) -> list[AIAnalysis]:
        return [a for a in self._store.values() if a.candidate_id == candidate_id][:limit]
