from app.domain.ai_analysis.enums import AnalysisStatus, AnalysisQualityTier, TaskType


def test_analysis_status_enum_values():
    assert AnalysisStatus.PENDING.value == "pending"
    assert AnalysisStatus.PROCESSING.value == "processing"
    assert AnalysisStatus.COMPLETED.value == "completed"
    assert AnalysisStatus.FAILED.value == "failed"
    assert len(AnalysisStatus) == 4


def test_task_type_enum_values():
    assert TaskType.EMBEDDING.value == "embedding"
    assert TaskType.EXTRACTION.value == "extraction"
    assert TaskType.SCORING.value == "scoring"
    assert TaskType.EXPLANATION.value == "explanation"
    assert len(TaskType) == 4


def test_quality_tier_enum_values():
    assert AnalysisQualityTier.FAST.value == "fast"
    assert AnalysisQualityTier.BALANCED.value == "balanced"
    assert AnalysisQualityTier.PRECISE.value == "precise"
    assert len(AnalysisQualityTier) == 3
