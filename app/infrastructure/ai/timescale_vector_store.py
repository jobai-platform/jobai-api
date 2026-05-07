from uuid import UUID

from sqlalchemy import text, select, delete as sql_delete
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.ai_analysis.ports import (
    CandidateEmbedding,
    JobEmbedding,
    SimilarityResult,
    VectorStorePort,
)
from app.infrastructure.persistence.models.embeddings import CandidateEmbeddingModel, JobEmbeddingModel


class TimescaleVectorStoreAdapter(VectorStorePort):

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def upsert_candidate(
        self,
        candidate_id: UUID,
        vector: list[float],
        metadata: dict,
    ) -> None:
        stmt = (
            insert(CandidateEmbeddingModel)
            .values(candidate_id=candidate_id, vector=vector, extra_metadata=metadata)
            .on_conflict_do_update(
                index_elements=["candidate_id"],
                set_={"vector": vector, "extra_metadata": metadata, "indexed_at": text("NOW()")},
            )
        )
        await self._session.execute(stmt)

    async def upsert_job(
        self,
        job_posting_id: UUID,
        vector: list[float],
        metadata: dict,
    ) -> None:
        stmt = (
            insert(JobEmbeddingModel)
            .values(job_posting_id=job_posting_id, vector=vector, extra_metadata=metadata)
            .on_conflict_do_update(
                index_elements=["job_posting_id"],
                set_={"vector": vector, "extra_metadata": metadata, "indexed_at": text("NOW()")},
            )
        )
        await self._session.execute(stmt)

    async def get_candidate(self, candidate_id: UUID) -> CandidateEmbedding | None:
        stmt = select(CandidateEmbeddingModel).where(
            CandidateEmbeddingModel.candidate_id == candidate_id
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        if model is None:
            return None
        return CandidateEmbedding(
            candidate_id=model.candidate_id,
            vector=model.vector,
            metadata=model.extra_metadata or {},
        )

    async def get_job(self, job_posting_id: UUID) -> JobEmbedding | None:
        stmt = select(JobEmbeddingModel).where(
            JobEmbeddingModel.job_posting_id == job_posting_id
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        if model is None:
            return None
        return JobEmbedding(
            job_posting_id=model.job_posting_id,
            vector=model.vector,
            metadata=model.extra_metadata or {},
        )

    async def search_similar_jobs(
        self,
        query_vector: list[float],
        top_k: int = 20,
        filters: dict | None = None,
    ) -> list[SimilarityResult]:
        vector_str = "[" + ",".join(map(str, query_vector)) + "]"
        query = text("""
            SELECT
                job_posting_id,
                1 - (vector <=> :query_vector::vector(768)) AS similarity,
                metadata
            FROM public.job_embeddings
            ORDER BY vector <=> :query_vector::vector(768)
            LIMIT :top_k
        """)
        result = await self._session.execute(query, {"query_vector": vector_str, "top_k": top_k})
        return [
            SimilarityResult(id=row[0], similarity_score=row[1], metadata=row[2] or {})
            for row in result.fetchall()
        ]

    async def search_similar_candidates(
        self,
        query_vector: list[float],
        top_k: int = 20,
        filters: dict | None = None,
    ) -> list[SimilarityResult]:
        vector_str = "[" + ",".join(map(str, query_vector)) + "]"
        query = text("""
            SELECT
                candidate_id,
                1 - (vector <=> :query_vector::vector(768)) AS similarity,
                metadata
            FROM public.candidate_embeddings
            ORDER BY vector <=> :query_vector::vector(768)
            LIMIT :top_k
        """)
        result = await self._session.execute(query, {"query_vector": vector_str, "top_k": top_k})
        return [
            SimilarityResult(id=row[0], similarity_score=row[1], metadata=row[2] or {})
            for row in result.fetchall()
        ]

    async def delete_candidate(self, candidate_id: UUID) -> None:
        stmt = sql_delete(CandidateEmbeddingModel).where(
            CandidateEmbeddingModel.candidate_id == candidate_id
        )
        await self._session.execute(stmt)

    async def delete_job(self, job_posting_id: UUID) -> None:
        stmt = sql_delete(JobEmbeddingModel).where(
            JobEmbeddingModel.job_posting_id == job_posting_id
        )
        await self._session.execute(stmt)
