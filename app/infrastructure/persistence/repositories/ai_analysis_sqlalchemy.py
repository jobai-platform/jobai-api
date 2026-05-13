from uuid import UUID

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.ai_analysis.ports import AIAnalysisRepository
from app.domain.ai_analysis.entities import AIAnalysis
from app.domain.ai_analysis.enums import AnalysisQualityTier, AnalysisStatus
from app.domain.ai_analysis.value_objects import MatchScore
from app.infrastructure.persistence.models.ai_analysis import AIAnalysisModel


def _to_domain(m: AIAnalysisModel) -> AIAnalysis:
    score = None
    if m.overall_score is not None:
        score = MatchScore(
            overall=m.overall_score,
            skills_score=m.skills_score or 0.0,
            experience_score=m.experience_score or 0.0,
            location_score=m.location_score or 0.0,
            salary_score=m.salary_score or 0.0,
            explanation=m.explanation or "",
        )
    return AIAnalysis(
        id=m.id,
        candidate_id=m.candidate_id,
        job_posting_id=m.job_posting_id,
        status=AnalysisStatus(m.status),
        match_score=score,
        quality_tier=AnalysisQualityTier(m.quality_tier) if m.quality_tier else None,
        tokens_consumed=m.tokens_consumed,
        created_at=m.created_at,
        completed_at=m.completed_at,
        failure_reason=m.failure_reason,
    )


def _score_kwargs(analysis: AIAnalysis) -> dict:
    if analysis.match_score is None:
        return {}
    s = analysis.match_score
    return {
        "overall_score": s.overall,
        "skills_score": s.skills_score,
        "experience_score": s.experience_score,
        "location_score": s.location_score,
        "salary_score": s.salary_score,
        "explanation": s.explanation,
    }


class SQLAlchemyAIAnalysisRepository(AIAnalysisRepository):

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, analysis: AIAnalysis) -> None:
        values = {
            "id": analysis.id,
            "candidate_id": analysis.candidate_id,
            "job_posting_id": analysis.job_posting_id,
            "status": analysis.status.value,
            "quality_tier": analysis.quality_tier.value if analysis.quality_tier else "balanced",
            "tokens_consumed": analysis.tokens_consumed,
            "failure_reason": analysis.failure_reason,
            "completed_at": analysis.completed_at,
            **_score_kwargs(analysis),
        }
        stmt = (
            insert(AIAnalysisModel)
            .values(**values)
            .on_conflict_do_update(
                constraint="uq_ai_analyses_candidate_job",
                set_={k: v for k, v in values.items() if k not in ("id", "candidate_id", "job_posting_id")},
            )
        )
        await self._session.execute(stmt)

    async def find_by_id(self, id: UUID) -> AIAnalysis | None:
        result = await self._session.execute(
            select(AIAnalysisModel).where(AIAnalysisModel.id == id)
        )
        m = result.scalar_one_or_none()
        return _to_domain(m) if m else None

    async def find_by_candidate_and_job(
        self,
        candidate_id: UUID,
        job_posting_id: UUID,
    ) -> AIAnalysis | None:
        result = await self._session.execute(
            select(AIAnalysisModel)
            .where(AIAnalysisModel.candidate_id == candidate_id)
            .where(AIAnalysisModel.job_posting_id == job_posting_id)
        )
        m = result.scalar_one_or_none()
        return _to_domain(m) if m else None

    async def find_by_candidate(
        self,
        candidate_id: UUID,
        limit: int = 20,
    ) -> list[AIAnalysis]:
        result = await self._session.execute(
            select(AIAnalysisModel)
            .where(AIAnalysisModel.candidate_id == candidate_id)
            .limit(limit)
        )
        return [_to_domain(m) for m in result.scalars().all()]
