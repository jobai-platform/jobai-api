from abc import ABC, abstractmethod
from dataclasses import dataclass
from uuid import UUID

from app.domain.ai_analysis.entities import AIAnalysis
from app.domain.ai_analysis.enums import AnalysisQualityTier
from app.domain.ai_analysis.value_objects import MatchScore


@dataclass(frozen=True, slots=True)
class SimilarityResult:
    id: UUID
    similarity_score: float
    metadata: dict


@dataclass(frozen=True, slots=True)
class CandidateEmbedding:
    candidate_id: UUID
    vector: list[float]
    metadata: dict


@dataclass(frozen=True, slots=True)
class JobEmbedding:
    job_posting_id: UUID
    vector: list[float]
    metadata: dict


class VectorStorePort(ABC):

    @abstractmethod
    async def upsert_candidate(
        self,
        candidate_id: UUID,
        vector: list[float],
        metadata: dict,
    ) -> None: ...

    @abstractmethod
    async def upsert_job(
        self,
        job_posting_id: UUID,
        vector: list[float],
        metadata: dict,
    ) -> None: ...

    @abstractmethod
    async def get_candidate(self, candidate_id: UUID) -> CandidateEmbedding | None: ...

    @abstractmethod
    async def get_job(self, job_posting_id: UUID) -> JobEmbedding | None: ...

    @abstractmethod
    async def search_similar_jobs(
        self,
        query_vector: list[float],
        top_k: int = 20,
        filters: dict | None = None,
    ) -> list[SimilarityResult]: ...

    @abstractmethod
    async def search_similar_candidates(
        self,
        query_vector: list[float],
        top_k: int = 20,
        filters: dict | None = None,
    ) -> list[SimilarityResult]: ...

    @abstractmethod
    async def delete_candidate(self, candidate_id: UUID) -> None: ...

    @abstractmethod
    async def delete_job(self, job_posting_id: UUID) -> None: ...


class AIAnalysisPipelinePort(ABC):
    """Runs the full matching pipeline for a candidate/job pair.

    Implementations: LangGraphMatchingPipeline (infra), FakeAIPipelinePort (tests).
    """

    @abstractmethod
    async def run(
        self,
        candidate_id: UUID,
        job_posting_id: UUID,
        tier: AnalysisQualityTier,
        analysis_id: UUID,
    ) -> MatchScore: ...


class AIAnalysisRepository(ABC):
    """Persists and retrieves AIAnalysis aggregates."""

    @abstractmethod
    async def save(self, analysis: AIAnalysis) -> None: ...

    @abstractmethod
    async def find_by_id(self, id: UUID) -> AIAnalysis | None: ...

    @abstractmethod
    async def find_by_candidate_and_job(
        self,
        candidate_id: UUID,
        job_posting_id: UUID,
    ) -> AIAnalysis | None: ...

    @abstractmethod
    async def find_by_candidate(
        self,
        candidate_id: UUID,
        limit: int = 20,
    ) -> list[AIAnalysis]: ...
