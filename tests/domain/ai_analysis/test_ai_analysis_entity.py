from datetime import UTC, datetime
from uuid import uuid4

import pytest

from app.domain.ai_analysis.entities import AIAnalysis
from app.domain.ai_analysis.enums import AnalysisQualityTier, AnalysisStatus
from app.domain.ai_analysis.value_objects import MatchScore


def test_create_ai_analysis_minimal():
    """Create AIAnalysis with minimal required fields"""
    analysis = AIAnalysis(
        id=uuid4(),
        candidate_id=uuid4(),
        job_posting_id=uuid4(),
        status=AnalysisStatus.PENDING,
        match_score=None,
        quality_tier=AnalysisQualityTier.BALANCED,
        tokens_consumed=0,
        created_at=datetime.now(UTC),
        completed_at=None
    )
    assert analysis.status == AnalysisStatus.PENDING
    assert analysis.match_score is None
    assert analysis.quality_tier == AnalysisQualityTier.BALANCED


def test_start_processing_from_pending():
    """Transition PENDING → PROCESSING"""
    analysis = AIAnalysis(
        id=uuid4(),
        candidate_id=uuid4(),
        job_posting_id=uuid4(),
        status=AnalysisStatus.PENDING,
        match_score=None,
        quality_tier=AnalysisQualityTier.FAST,
        tokens_consumed=0,
        created_at=datetime.now(UTC),
        completed_at=None
    )
    analysis.start_processing()
    assert analysis.status == AnalysisStatus.PROCESSING


def test_start_processing_from_completed_fails():
    """start_processing() refuses since COMPLETED"""
    analysis = AIAnalysis(
        id=uuid4(),
        candidate_id=uuid4(),
        job_posting_id=uuid4(),
        status=AnalysisStatus.COMPLETED,
        match_score=MatchScore(0.8, 0.9, 0.7, 1.0, 0.6, "Good"),
        quality_tier=AnalysisQualityTier.BALANCED,
        tokens_consumed=1500,
        created_at=datetime.now(UTC),
        completed_at=datetime.now(UTC)
    )
    with pytest.raises(ValueError, match="Cannot start processing from COMPLETED"):
        analysis.start_processing()


def test_complete_analysis_with_score():
    """Transition PROCESSING → COMPLETED with MatchScore"""
    analysis = AIAnalysis(
        id=uuid4(),
        candidate_id=uuid4(),
        job_posting_id=uuid4(),
        status=AnalysisStatus.PROCESSING,
        match_score=None,
        quality_tier=AnalysisQualityTier.PRECISE,
        tokens_consumed=0,
        created_at=datetime.now(UTC),
        completed_at=None
    )

    score = MatchScore(0.85, 0.9, 0.8, 1.0, 0.75, "Strong match")
    analysis.complete(score)

    assert analysis.status == AnalysisStatus.COMPLETED
    assert analysis.match_score == score
    assert analysis.completed_at is not None


def test_complete_analysis_from_pending_fails():
    """complete() refuses since PENDING"""
    analysis = AIAnalysis(
        id=uuid4(),
        candidate_id=uuid4(),
        job_posting_id=uuid4(),
        status=AnalysisStatus.PENDING,
        match_score=None,
        quality_tier=AnalysisQualityTier.BALANCED,
        tokens_consumed=0,
        created_at=datetime.now(UTC),
        completed_at=None
    )

    score = MatchScore(0.85, 0.9, 0.8, 1.0, 0.75, "Strong match")
    with pytest.raises(ValueError, match="Cannot complete from PENDING"):
        analysis.complete(score)


def test_fail_analysis_with_reason():
    """Transition PROCESSING → FAILED with raison"""
    analysis = AIAnalysis(
        id=uuid4(),
        candidate_id=uuid4(),
        job_posting_id=uuid4(),
        status=AnalysisStatus.PROCESSING,
        match_score=None,
        quality_tier=AnalysisQualityTier.BALANCED,
        tokens_consumed=500,
        created_at=datetime.now(UTC),
        completed_at=None
    )

    analysis.fail("Model timeout after 3 retries")

    assert analysis.status == AnalysisStatus.FAILED
    assert "timeout" in analysis.failure_reason.lower()
    assert analysis.completed_at is not None


def test_fail_analysis_from_pending_fails():
    """fail() refuses since PENDING"""
    analysis = AIAnalysis(
        id=uuid4(),
        candidate_id=uuid4(),
        job_posting_id=uuid4(),
        status=AnalysisStatus.PENDING,
        match_score=None,
        quality_tier=AnalysisQualityTier.BALANCED,
        tokens_consumed=0,
        created_at=datetime.now(UTC),
        completed_at=None
    )

    with pytest.raises(ValueError, match="Cannot fail from PENDING"):
        analysis.fail("Some reason")


def _make_analysis(status: AnalysisStatus = AnalysisStatus.PENDING) -> AIAnalysis:
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


def test_reset_for_retry_from_failed_sets_status_to_pending():
    analysis = _make_analysis(AnalysisStatus.PENDING)
    # manually set to FAILED state
    analysis.status = AnalysisStatus.FAILED
    analysis.failure_reason = "timeout"
    analysis.completed_at = datetime.now(UTC)  # make assertion load-bearing

    analysis.reset_for_retry()

    assert analysis.status == AnalysisStatus.PENDING
    assert analysis.failure_reason is None
    assert analysis.completed_at is None


def test_reset_for_retry_raises_when_status_is_not_failed():
    analysis = _make_analysis(AnalysisStatus.PENDING)
    with pytest.raises(ValueError, match="Cannot retry"):
        analysis.reset_for_retry()
