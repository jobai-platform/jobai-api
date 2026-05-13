from uuid import UUID

from app.application.ai_analysis.ports import AIAnalysisPipelinePort
from app.domain.ai_analysis.enums import AnalysisQualityTier
from app.domain.ai_analysis.value_objects import MatchScore


class FakeAIPipelinePort(AIAnalysisPipelinePort):
    """Returns a configurable MatchScore without running any LLM."""

    def __init__(self, default_score: MatchScore | None = None) -> None:
        self._score = default_score or MatchScore(
            overall=0.75,
            skills_score=0.8,
            experience_score=0.7,
            location_score=0.9,
            salary_score=0.6,
            explanation="Fake pipeline response.",
        )
        self.calls: list[dict] = []

    async def run(
        self,
        candidate_id: UUID,
        job_posting_id: UUID,
        tier: AnalysisQualityTier,
        analysis_id: UUID,
    ) -> MatchScore:
        self.calls.append(
            {
                "candidate_id": candidate_id,
                "job_posting_id": job_posting_id,
                "tier": tier,
                "analysis_id": analysis_id,
            }
        )
        return self._score
