from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.application.ai_analysis.ports import AIAnalysisPipelinePort
from app.domain.ai_analysis.enums import AnalysisQualityTier
from app.domain.ai_analysis.ports import EmbeddingPort
from app.domain.ai_analysis.value_objects import MatchScore
from app.infrastructure.ai.pipeline.graph import LangGraphMatchingPipeline
from app.infrastructure.ai.timescale_vector_store import TimescaleVectorStoreAdapter
from app.infrastructure.persistence.repositories.candidate_profile_sqlalchemy import (
    SQLAlchemyCandidateProfileRepository,
)
from app.infrastructure.persistence.repositories.job_posting_sqlalchemy import (
    JobPostingSQLAlchemyRepository,
)


class LangGraphPipelineAdapter(AIAnalysisPipelinePort):
    def __init__(
        self,
        session: AsyncSession,
        llm: object,
        embedding_port: EmbeddingPort,
    ) -> None:
        self._session = session
        self._llm = llm
        self._embedding_port = embedding_port

    async def run(
        self,
        candidate_id: UUID,
        job_posting_id: UUID,
        tier: AnalysisQualityTier,
        analysis_id: UUID,
    ) -> MatchScore:
        profile_repo = SQLAlchemyCandidateProfileRepository(self._session)
        job_repo = JobPostingSQLAlchemyRepository(self._session)

        profile = await profile_repo.get_by_user_id(candidate_id)
        job = await job_repo.get_by_id(job_posting_id)

        profile_parts = []
        if profile is not None:
            if profile.current_title:
                profile_parts.append(profile.current_title)
            if profile.skills:
                profile_parts.append(" ".join(profile.skills))
            if profile.bio:
                profile_parts.append(profile.bio)

        pipeline = LangGraphMatchingPipeline(
            llm=self._llm,
            embedding_port=self._embedding_port,
            vector_store=TimescaleVectorStoreAdapter(self._session),
            candidate_text=" ".join(profile_parts),
            job_text=job.description if job is not None else "",
        )
        return await pipeline.run(candidate_id, job_posting_id, tier, analysis_id)
