from abc import ABC, abstractmethod
from dataclasses import dataclass
from uuid import UUID


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
