from datetime import UTC, datetime
from uuid import uuid4

import pytest

from app.application.ai_analysis.use_cases import GetAnalysisUseCase
from app.domain.ai_analysis.entities import AIAnalysis
from app.domain.ai_analysis.enums import AnalysisQualityTier, AnalysisStatus
from app.domain.common.exceptions import NotFoundError
from tests.fakes.ai_analysis.in_memory_ai_analysis_repo import InMemoryAIAnalysisRepository


def _make_analysis(status: AnalysisStatus = AnalysisStatus.COMPLETED) -> AIAnalysis:
    return AIAnalysis(
        id=uuid4(),
        candidate_id=uuid4(),
        job_posting_id=uuid4(),
        status=status,
        match_score=None,
        quality_tier=AnalysisQualityTier.FAST,
        tokens_consumed=0,
        created_at=datetime.now(UTC),
        completed_at=None,
    )


@pytest.mark.asyncio
async def test_get_analysis_returns_analysis_when_found():
    repo = InMemoryAIAnalysisRepository()
    analysis = _make_analysis()
    await repo.save(analysis)

    use_case = GetAnalysisUseCase(repo=repo)
    result = await use_case.execute(analysis_id=analysis.id)

    assert result.id == analysis.id
    assert result.status == AnalysisStatus.COMPLETED


@pytest.mark.asyncio
async def test_get_analysis_raises_not_found_when_missing():
    repo = InMemoryAIAnalysisRepository()
    use_case = GetAnalysisUseCase(repo=repo)

    with pytest.raises(NotFoundError):
        await use_case.execute(analysis_id=uuid4())
