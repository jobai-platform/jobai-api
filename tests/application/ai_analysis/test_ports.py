import pytest

from app.application.ai_analysis.ports import AIAnalysisPipelinePort, AIAnalysisRepository


def test_pipeline_port_is_abstract():
    """AIAnalysisPipelinePort cannot be instantiated directly."""
    with pytest.raises(TypeError):
        AIAnalysisPipelinePort()  # type: ignore


def test_analysis_repository_is_abstract():
    """AIAnalysisRepository cannot be instantiated directly."""
    with pytest.raises(TypeError):
        AIAnalysisRepository()  # type: ignore
