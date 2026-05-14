from dataclasses import dataclass
from datetime import datetime, UTC
from uuid import UUID

from app.domain.ai_analysis.enums import AnalysisStatus, AnalysisQualityTier
from app.domain.ai_analysis.value_objects import MatchScore

@dataclass(slots=True)
class AIAnalysis:
    id: UUID
    candidate_id: UUID
    job_posting_id: UUID
    status: AnalysisStatus
    match_score: MatchScore | None
    quality_tier: AnalysisQualityTier | None
    tokens_consumed: int
    created_at: datetime
    completed_at: datetime | None
    failure_reason: str | None = None

    def start_processing(self) -> None:
        if self.status != AnalysisStatus.PENDING:
            raise ValueError(
                f"Cannot start processing from {self.status.name}. "
                f"Expected status: {AnalysisStatus.PENDING.name}"
            )
        self.status = AnalysisStatus.PROCESSING

    def complete(self, score: MatchScore) -> None:
        if self.status != AnalysisStatus.PROCESSING:
            raise ValueError(
                f"Cannot complete from {self.status.name}. "
                f"Expected status: {AnalysisStatus.PROCESSING.name}"
            )
        self.status = AnalysisStatus.COMPLETED
        self.match_score = score
        self.completed_at = datetime.now(UTC)

    def fail(self, reason: str) -> None:
        if self.status != AnalysisStatus.PROCESSING:
            raise ValueError(
                f"Cannot fail from {self.status.name}. "
                f"Expected status: {AnalysisStatus.PROCESSING.name}"
            )
        self.status = AnalysisStatus.FAILED
        self.failure_reason = reason
        self.completed_at = datetime.now(UTC)

    def reset_for_retry(self) -> None:
        if self.status != AnalysisStatus.FAILED:
            raise ValueError(
                f"Cannot retry from {self.status.name}. Expected status: {AnalysisStatus.FAILED.name}"
            )
        self.status = AnalysisStatus.PENDING
        self.failure_reason = None
        self.completed_at = None

