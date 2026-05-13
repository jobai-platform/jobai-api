from typing import TypedDict
from uuid import UUID

from app.domain.ai_analysis.enums import AnalysisQualityTier
from app.domain.ai_analysis.value_objects import MatchScore


class PipelineState(TypedDict):
    candidate_id: UUID
    job_posting_id: UUID
    analysis_id: UUID
    tier: AnalysisQualityTier
    structured_profile: dict | None
    structured_job: dict | None
    context_jobs: list[dict]
    raw_scores: dict | None
    match_score: MatchScore | None
    retry_count: int
    error: str | None
    _candidate_text: str
    _job_text: str
    _prev_retry_count: int


def make_initial_state(
    candidate_id: UUID,
    job_posting_id: UUID,
    tier: AnalysisQualityTier,
    analysis_id: UUID,
    candidate_text: str = "",
    job_text: str = "",
) -> PipelineState:
    return PipelineState(
        candidate_id=candidate_id,
        job_posting_id=job_posting_id,
        analysis_id=analysis_id,
        tier=tier,
        structured_profile=None,
        structured_job=None,
        context_jobs=[],
        raw_scores=None,
        match_score=None,
        retry_count=0,
        error=None,
        _candidate_text=candidate_text,
        _job_text=job_text,
        _prev_retry_count=0,
    )
