import math
from uuid import UUID

from app.application.ai_analysis.ports import (
    CandidateEmbedding,
    JobEmbedding,
    SimilarityResult,
    VectorStorePort,
)


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot / (norm_a * norm_b)


class FakeVectorStore(VectorStorePort):

    def __init__(self) -> None:
        self._candidates: dict[UUID, CandidateEmbedding] = {}
        self._jobs: dict[UUID, JobEmbedding] = {}

    async def upsert_candidate(self, candidate_id: UUID, vector: list[float], metadata: dict) -> None:
        self._candidates[candidate_id] = CandidateEmbedding(
            candidate_id=candidate_id, vector=vector, metadata=metadata
        )

    async def upsert_job(self, job_posting_id: UUID, vector: list[float], metadata: dict) -> None:
        self._jobs[job_posting_id] = JobEmbedding(
            job_posting_id=job_posting_id, vector=vector, metadata=metadata
        )

    async def get_candidate(self, candidate_id: UUID) -> CandidateEmbedding | None:
        return self._candidates.get(candidate_id)

    async def get_job(self, job_posting_id: UUID) -> JobEmbedding | None:
        return self._jobs.get(job_posting_id)

    async def search_similar_jobs(
        self,
        query_vector: list[float],
        top_k: int = 20,
        filters: dict | None = None,
    ) -> list[SimilarityResult]:
        scored = [
            SimilarityResult(id=jid, similarity_score=_cosine_similarity(query_vector, emb.vector), metadata=emb.metadata)
            for jid, emb in self._jobs.items()
        ]
        scored.sort(key=lambda r: r.similarity_score, reverse=True)
        return scored[:top_k]

    async def search_similar_candidates(
        self,
        query_vector: list[float],
        top_k: int = 20,
        filters: dict | None = None,
    ) -> list[SimilarityResult]:
        scored = [
            SimilarityResult(id=cid, similarity_score=_cosine_similarity(query_vector, emb.vector), metadata=emb.metadata)
            for cid, emb in self._candidates.items()
        ]
        scored.sort(key=lambda r: r.similarity_score, reverse=True)
        return scored[:top_k]

    async def delete_candidate(self, candidate_id: UUID) -> None:
        self._candidates.pop(candidate_id, None)

    async def delete_job(self, job_posting_id: UUID) -> None:
        self._jobs.pop(job_posting_id, None)
