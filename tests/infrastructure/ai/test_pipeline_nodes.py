import pytest
from unittest.mock import AsyncMock
from uuid import uuid4

from app.domain.ai_analysis.enums import AnalysisQualityTier
from app.infrastructure.ai.pipeline.state import make_initial_state
from app.infrastructure.ai.pipeline.nodes import (
    profile_extractor_node,
    job_extractor_node,
    semantic_retriever_node,
    scorer_node,
    reporter_node,
)
from app.application.ai_analysis.ports import SimilarityResult
from app.domain.ai_analysis.value_objects import MatchScore


@pytest.fixture
def base_state():
    return make_initial_state(
        candidate_id=uuid4(),
        job_posting_id=uuid4(),
        tier=AnalysisQualityTier.FAST,
        analysis_id=uuid4(),
    )


@pytest.mark.asyncio
async def test_profile_extractor_node_returns_structured_profile(base_state):
    """GIVEN a state with candidate text
    WHEN profile_extractor_node is called with a mocked LLM
    THEN structured_profile is populated with parsed JSON
    """
    base_state["_candidate_text"] = "Python developer, 5 years, Geneva"

    mock_llm = AsyncMock()
    mock_llm.ainvoke = AsyncMock(
        return_value='{"skills": ["Python"], "experience_years": 5, "locations": ["Geneva"], "salary_range": null}'
    )

    result = await profile_extractor_node(base_state, llm=mock_llm)

    assert result["structured_profile"] is not None
    assert result["structured_profile"]["skills"] == ["Python"]
    assert result["structured_profile"]["experience_years"] == 5
    assert result["error"] is None


@pytest.mark.asyncio
async def test_profile_extractor_node_handles_invalid_json(base_state):
    """GIVEN the LLM returns non-JSON text
    WHEN profile_extractor_node is called
    THEN error is set and structured_profile is None
    """
    base_state["_candidate_text"] = "some text"

    mock_llm = AsyncMock()
    mock_llm.ainvoke = AsyncMock(return_value="Sorry, I cannot help with that.")

    result = await profile_extractor_node(base_state, llm=mock_llm)

    assert result["structured_profile"] is None
    assert result["error"] is not None
    assert "JSON" in result["error"]


@pytest.mark.asyncio
async def test_job_extractor_node_returns_structured_job(base_state):
    """GIVEN a state with job description text
    WHEN job_extractor_node is called with a mocked LLM
    THEN structured_job is populated
    """
    base_state["_job_text"] = "Senior Python Engineer, remote, 100k-130k CHF"

    mock_llm = AsyncMock()
    mock_llm.ainvoke = AsyncMock(
        return_value='{"required_skills": ["Python"], "seniority": "Senior", "location": "Remote", "salary_range": {"min": 100000, "max": 130000}}'
    )

    result = await job_extractor_node(base_state, llm=mock_llm)

    assert result["structured_job"] is not None
    assert result["structured_job"]["seniority"] == "Senior"
    assert result["error"] is None


@pytest.mark.asyncio
async def test_semantic_retriever_node_returns_context_jobs(base_state):
    """GIVEN structured_profile is set
    WHEN semantic_retriever_node is called with mocked embedding + vector store
    THEN context_jobs is populated with similarity results
    """
    base_state["structured_profile"] = {"skills": ["Python"], "experience_years": 5}

    mock_embedding = AsyncMock()
    mock_embedding.generate_embedding = AsyncMock(return_value=[0.1] * 768)

    mock_vector_store = AsyncMock()
    mock_vector_store.search_similar_jobs = AsyncMock(
        return_value=[
            SimilarityResult(id=uuid4(), similarity_score=0.85, metadata={"title": "Python Dev"}),
        ]
    )

    result = await semantic_retriever_node(
        base_state, embedding_port=mock_embedding, vector_store=mock_vector_store
    )

    assert len(result["context_jobs"]) == 1
    assert result["context_jobs"][0]["similarity_score"] == 0.85
    assert result["error"] is None


@pytest.mark.asyncio
async def test_semantic_retriever_retries_when_low_confidence(base_state):
    """GIVEN max similarity < 0.6 on first attempt
    WHEN semantic_retriever_node is called
    THEN retry_count is incremented
    """
    base_state["structured_profile"] = {"skills": ["Python"]}
    base_state["retry_count"] = 0

    mock_embedding = AsyncMock()
    mock_embedding.generate_embedding = AsyncMock(return_value=[0.1] * 768)

    mock_vector_store = AsyncMock()
    mock_vector_store.search_similar_jobs = AsyncMock(
        return_value=[
            SimilarityResult(id=uuid4(), similarity_score=0.4, metadata={}),
        ]
    )

    result = await semantic_retriever_node(
        base_state, embedding_port=mock_embedding, vector_store=mock_vector_store
    )

    assert result["retry_count"] == 1


@pytest.mark.asyncio
async def test_scorer_node_returns_raw_scores(base_state):
    """GIVEN structured_profile, structured_job, and context_jobs are set
    WHEN scorer_node is called with mocked LLM
    THEN raw_scores is populated with 4 float scores
    """
    base_state["structured_profile"] = {"skills": ["Python"], "experience_years": 5}
    base_state["structured_job"] = {"required_skills": ["Python"], "seniority": "Senior"}
    base_state["context_jobs"] = []

    mock_llm = AsyncMock()
    mock_llm.ainvoke = AsyncMock(
        return_value='{"skills": 0.9, "experience": 0.7, "location": 1.0, "salary": 0.8}'
    )

    result = await scorer_node(base_state, llm=mock_llm)

    assert result["raw_scores"] is not None
    assert result["raw_scores"]["skills"] == 0.9
    assert result["error"] is None


@pytest.mark.asyncio
async def test_reporter_node_returns_match_score(base_state):
    """GIVEN raw_scores are set
    WHEN reporter_node is called with mocked LLM
    THEN match_score VO is returned with valid scores and explanation
    """
    base_state["structured_profile"] = {"skills": ["Python"]}
    base_state["structured_job"] = {"required_skills": ["Python"]}
    base_state["raw_scores"] = {"skills": 0.9, "experience": 0.7, "location": 1.0, "salary": 0.8}

    mock_llm = AsyncMock()
    mock_llm.ainvoke = AsyncMock(
        return_value="Strong Python skills match. Experience slightly below requirement."
    )

    result = await reporter_node(base_state, llm=mock_llm)

    assert result["match_score"] is not None
    assert isinstance(result["match_score"], MatchScore)
    assert 0.0 <= result["match_score"].overall <= 1.0
    assert len(result["match_score"].explanation) > 0
