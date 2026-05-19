from __future__ import annotations

from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.application.ai_analysis.ports import SimilarityResult
from app.domain.ai_analysis.entities import AIAnalysis
from app.domain.ai_analysis.enums import AnalysisQualityTier, AnalysisStatus


class ComputeMatchRequest(BaseModel):
    model_config = ConfigDict(strict=True)

    candidate_id: UUID = Field(strict=False)
    job_posting_id: UUID = Field(strict=False)


class IndexJobPostingRequest(BaseModel):
    model_config = ConfigDict(strict=True)

    description: str = Field(min_length=1)


class MatchScoreResponse(BaseModel):
    overall: Annotated[float, Field(ge=0.0, le=1.0)]
    skills_score: Annotated[float, Field(ge=0.0, le=1.0)]
    experience_score: Annotated[float, Field(ge=0.0, le=1.0)]
    location_score: Annotated[float, Field(ge=0.0, le=1.0)]
    salary_score: Annotated[float, Field(ge=0.0, le=1.0)]
    explanation: str


class AnalysisResponse(BaseModel):
    id: UUID
    candidate_id: UUID
    job_posting_id: UUID
    status: AnalysisStatus
    quality_tier: AnalysisQualityTier | None = None
    match_score: MatchScoreResponse | None = None
    tokens_consumed: int
    created_at: datetime
    completed_at: datetime | None = None
    failure_reason: str | None = None

    @classmethod
    def from_domain(cls, analysis: AIAnalysis) -> AnalysisResponse:
        match_score = None
        if analysis.match_score is not None:
            score = analysis.match_score
            match_score = MatchScoreResponse(
                overall=score.overall,
                skills_score=score.skills_score,
                experience_score=score.experience_score,
                location_score=score.location_score,
                salary_score=score.salary_score,
                explanation=score.explanation,
            )

        return cls(
            id=analysis.id,
            candidate_id=analysis.candidate_id,
            job_posting_id=analysis.job_posting_id,
            status=analysis.status,
            quality_tier=analysis.quality_tier,
            match_score=match_score,
            tokens_consumed=analysis.tokens_consumed,
            created_at=analysis.created_at,
            completed_at=analysis.completed_at,
            failure_reason=analysis.failure_reason,
        )


class JobMatchResponse(BaseModel):
    id: UUID
    similarity_score: float
    metadata: dict

    @classmethod
    def from_domain(cls, result: SimilarityResult) -> JobMatchResponse:
        return cls(
            id=result.id,
            similarity_score=result.similarity_score,
            metadata=result.metadata,
        )
