from datetime import UTC, datetime
from uuid import uuid4

import pytest

from app.application.ai_analysis.use_cases import ComputeMatchScoreCommand, ComputeMatchScoreUseCase
from app.domain.ai_analysis.entities import AIAnalysis
from app.domain.ai_analysis.enums import AnalysisQualityTier, AnalysisStatus
from app.domain.ai_analysis.value_objects import MatchScore
from tests.fakes.ai_analysis.fake_pipeline_port import FakeAIPipelinePort
from tests.fakes.ai_analysis.in_memory_ai_analysis_repo import InMemoryAIAnalysisRepository


def _make_analysis(status: AnalysisStatus, candidate_id=None, job_posting_id=None) -> AIAnalysis:
    return AIAnalysis(
        id=uuid4(),
        candidate_id=candidate_id or uuid4(),
        job_posting_id=job_posting_id or uuid4(),
        status=status,
        match_score=None,
        quality_tier=AnalysisQualityTier.FAST,
        tokens_consumed=0,
        created_at=datetime.now(UTC),
        completed_at=None,
    )


def _make_completed_analysis(candidate_id=None, job_posting_id=None) -> AIAnalysis:
    score = MatchScore(
        overall=0.9,
        skills_score=0.9,
        experience_score=0.9,
        location_score=0.9,
        salary_score=0.9,
        explanation="cached",
    )
    a = _make_analysis(AnalysisStatus.COMPLETED, candidate_id, job_posting_id)
    a.match_score = score
    return a


@pytest.mark.asyncio
async def test_returns_cached_analysis_when_completed():
    repo = InMemoryAIAnalysisRepository()
    pipeline = FakeAIPipelinePort()
    candidate_id, job_id = uuid4(), uuid4()
    cached = _make_completed_analysis(candidate_id=candidate_id, job_posting_id=job_id)
    await repo.save(cached)

    use_case = ComputeMatchScoreUseCase(repo=repo, pipeline=pipeline)
    result = await use_case.execute(
        ComputeMatchScoreCommand(candidate_id=candidate_id, job_posting_id=job_id)
    )

    assert result.id == cached.id
    assert result.status == AnalysisStatus.COMPLETED
    assert len(pipeline.calls) == 0  # pipeline NOT called for cache hit


@pytest.mark.asyncio
async def test_returns_in_progress_analysis_without_running_pipeline():
    repo = InMemoryAIAnalysisRepository()
    pipeline = FakeAIPipelinePort()
    candidate_id, job_id = uuid4(), uuid4()
    in_progress = _make_analysis(AnalysisStatus.PROCESSING, candidate_id, job_id)
    await repo.save(in_progress)

    use_case = ComputeMatchScoreUseCase(repo=repo, pipeline=pipeline)
    result = await use_case.execute(
        ComputeMatchScoreCommand(candidate_id=candidate_id, job_posting_id=job_id)
    )

    assert result.status == AnalysisStatus.PROCESSING
    assert len(pipeline.calls) == 0


@pytest.mark.asyncio
async def test_returns_pending_analysis_without_running_pipeline():
    repo = InMemoryAIAnalysisRepository()
    pipeline = FakeAIPipelinePort()
    candidate_id, job_id = uuid4(), uuid4()
    pending = _make_analysis(AnalysisStatus.PENDING, candidate_id, job_id)
    await repo.save(pending)

    use_case = ComputeMatchScoreUseCase(repo=repo, pipeline=pipeline)
    result = await use_case.execute(
        ComputeMatchScoreCommand(candidate_id=candidate_id, job_posting_id=job_id)
    )

    assert result.status == AnalysisStatus.PENDING
    assert len(pipeline.calls) == 0


@pytest.mark.asyncio
async def test_creates_new_analysis_and_runs_pipeline_when_no_existing():
    repo = InMemoryAIAnalysisRepository()
    pipeline = FakeAIPipelinePort()
    candidate_id, job_id = uuid4(), uuid4()

    use_case = ComputeMatchScoreUseCase(repo=repo, pipeline=pipeline)
    result = await use_case.execute(
        ComputeMatchScoreCommand(
            candidate_id=candidate_id,
            job_posting_id=job_id,
            tier=AnalysisQualityTier.BALANCED,
        )
    )

    assert result.status == AnalysisStatus.COMPLETED
    assert result.match_score is not None
    assert result.match_score.overall == 0.75  # FakeAIPipelinePort default
    assert len(pipeline.calls) == 1
    assert pipeline.calls[0]["tier"] == AnalysisQualityTier.BALANCED


@pytest.mark.asyncio
async def test_resets_failed_analysis_and_reruns_pipeline():
    repo = InMemoryAIAnalysisRepository()
    pipeline = FakeAIPipelinePort()
    candidate_id, job_id = uuid4(), uuid4()

    failed = _make_analysis(AnalysisStatus.FAILED, candidate_id, job_id)
    failed.failure_reason = "timeout"
    await repo.save(failed)

    use_case = ComputeMatchScoreUseCase(repo=repo, pipeline=pipeline)
    result = await use_case.execute(
        ComputeMatchScoreCommand(candidate_id=candidate_id, job_posting_id=job_id)
    )

    assert result.status == AnalysisStatus.COMPLETED
    assert result.failure_reason is None
    assert len(pipeline.calls) == 1


@pytest.mark.asyncio
async def test_marks_analysis_as_failed_when_pipeline_raises():
    repo = InMemoryAIAnalysisRepository()
    candidate_id, job_id = uuid4(), uuid4()

    class FailingPipeline(FakeAIPipelinePort):
        async def run(self, candidate_id, job_posting_id, tier, analysis_id):
            raise RuntimeError("LLM unavailable")

    use_case = ComputeMatchScoreUseCase(repo=repo, pipeline=FailingPipeline())

    with pytest.raises(RuntimeError, match="LLM unavailable"):
        await use_case.execute(
            ComputeMatchScoreCommand(candidate_id=candidate_id, job_posting_id=job_id)
        )

    # The analysis should have been saved as FAILED
    saved = await repo.find_by_candidate_and_job(candidate_id, job_id)
    assert saved is not None
    assert saved.status == AnalysisStatus.FAILED
    assert "LLM unavailable" in (saved.failure_reason or "")
