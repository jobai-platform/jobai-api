import pytest
from unittest.mock import AsyncMock
from uuid import uuid4

from app.domain.ai_analysis.enums import AnalysisQualityTier
from app.domain.ai_analysis.value_objects import MatchScore
from app.application.ai_analysis.ports import SimilarityResult
from app.infrastructure.ai.pipeline.graph import LangGraphMatchingPipeline


@pytest.fixture
def mock_llm():
    llm = AsyncMock()
    llm.ainvoke = AsyncMock()
    return llm


@pytest.fixture
def mock_embedding():
    emb = AsyncMock()
    emb.generate_embedding = AsyncMock(return_value=[0.1] * 768)
    return emb


@pytest.fixture
def mock_vector_store():
    vs = AsyncMock()
    vs.search_similar_jobs = AsyncMock(
        return_value=[
            SimilarityResult(id=uuid4(), similarity_score=0.8, metadata={"title": "Python Dev"})
        ]
    )
    return vs


@pytest.mark.asyncio
async def test_pipeline_run_returns_match_score(mock_llm, mock_embedding, mock_vector_store):
    """GIVEN all nodes succeed with mocked LLM and vector store
    WHEN pipeline.run() is called
    THEN a MatchScore is returned
    """
    mock_llm.ainvoke.side_effect = [
        '{"skills": ["Python"], "experience_years": 5, "locations": ["Geneva"], "salary_range": null}',
        '{"required_skills": ["Python"], "seniority": "Senior", "location": "Remote", "salary_range": null}',
        '{"skills": 0.9, "experience": 0.7, "location": 1.0, "salary": 0.8}',
        "Strong Python skills. Some experience gap.",
    ]

    pipeline = LangGraphMatchingPipeline(
        llm=mock_llm,
        embedding_port=mock_embedding,
        vector_store=mock_vector_store,
        candidate_text="Python dev, 5 years, Geneva",
        job_text="Senior Python Engineer, remote",
    )

    score = await pipeline.run(
        candidate_id=uuid4(),
        job_posting_id=uuid4(),
        tier=AnalysisQualityTier.FAST,
        analysis_id=uuid4(),
    )

    assert isinstance(score, MatchScore)
    assert 0.0 <= score.overall <= 1.0
    assert len(score.explanation) > 0


@pytest.mark.asyncio
async def test_pipeline_raises_when_profile_extraction_fails(mock_llm, mock_embedding, mock_vector_store):
    """GIVEN the LLM returns non-JSON on profile extraction
    WHEN pipeline.run() is called
    THEN RuntimeError is raised with informative message
    """
    mock_llm.ainvoke.side_effect = ["Not valid JSON at all"]

    pipeline = LangGraphMatchingPipeline(
        llm=mock_llm,
        embedding_port=mock_embedding,
        vector_store=mock_vector_store,
        candidate_text="Python dev",
        job_text="Python job",
    )

    with pytest.raises(RuntimeError, match="profile_extractor"):
        await pipeline.run(
            candidate_id=uuid4(),
            job_posting_id=uuid4(),
            tier=AnalysisQualityTier.FAST,
            analysis_id=uuid4(),
        )
