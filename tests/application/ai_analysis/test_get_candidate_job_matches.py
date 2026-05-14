from uuid import uuid4

import pytest

from app.application.ai_analysis.ports import SimilarityResult
from app.application.ai_analysis.use_cases import GetCandidateJobMatchesUseCase
from app.domain.common.exceptions import NotFoundError
from tests.fakes.ai_analysis.fake_vector_store import FakeVectorStore


@pytest.mark.asyncio
async def test_returns_top_k_similar_jobs():
    vector_store = FakeVectorStore()
    candidate_id = uuid4()

    # Index candidate
    await vector_store.upsert_candidate(candidate_id, [1.0, 0.0, 0.0], {})

    # Index 3 jobs with different similarity profiles
    job_a = uuid4()
    job_b = uuid4()
    job_c = uuid4()
    await vector_store.upsert_job(job_a, [1.0, 0.0, 0.0], {"title": "Python Dev"})  # most similar
    await vector_store.upsert_job(job_b, [0.5, 0.5, 0.0], {"title": "Full Stack"})  # medium
    await vector_store.upsert_job(job_c, [0.0, 0.0, 1.0], {"title": "DevOps"})  # least similar

    use_case = GetCandidateJobMatchesUseCase(vector_store=vector_store)
    results = await use_case.execute(candidate_id=candidate_id, top_k=2)

    assert len(results) == 2
    assert results[0].id == job_a  # highest similarity first
    assert results[0].similarity_score > results[1].similarity_score


@pytest.mark.asyncio
async def test_raises_not_found_when_candidate_not_indexed():
    vector_store = FakeVectorStore()
    use_case = GetCandidateJobMatchesUseCase(vector_store=vector_store)

    with pytest.raises(NotFoundError):
        await use_case.execute(candidate_id=uuid4(), top_k=10)


@pytest.mark.asyncio
async def test_returns_empty_list_when_no_jobs_indexed():
    vector_store = FakeVectorStore()
    candidate_id = uuid4()
    await vector_store.upsert_candidate(candidate_id, [1.0, 0.0, 0.0], {})

    use_case = GetCandidateJobMatchesUseCase(vector_store=vector_store)
    results = await use_case.execute(candidate_id=candidate_id, top_k=10)

    assert results == []
