from app.domain.ai_analysis.enums import AnalysisStatus, AnalysisQualityTier


def test_analysis_status_enum_values():
    """Verify that the AnalysisStatus enum has the expected values."""
    assert AnalysisStatus.PENDING.value == "pending"
    assert AnalysisStatus.PROCESSING.value == "processing"
    assert AnalysisStatus.COMPLETED.value == "completed"
    assert AnalysisStatus.FAILED.value == "failed"
    assert len(AnalysisStatus) == 4


def test_task_type_enum_values():
    """Verify that the TaskType enum has the expected values."""
    assert AnalysisQualityTier.FAST.value == "fast"
    assert AnalysisQualityTier.BALANCED.value == "balanced"
    assert AnalysisQualityTier.PRECISE.value == "precise"
    assert len(AnalysisQualityTier) == 3


def test_quality_tier_ordering():
    """Verify that the QualityTier ordering is correct."""
    tiers = [
        AnalysisQualityTier.FAST,
        AnalysisQualityTier.BALANCED,
        AnalysisQualityTier.PRECISE,
    ]
    assert tiers[0] == AnalysisQualityTier.FAST
    assert tiers[1] == AnalysisQualityTier.BALANCED
    assert tiers[2] == AnalysisQualityTier.PRECISE
