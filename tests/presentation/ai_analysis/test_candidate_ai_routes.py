from datetime import UTC, datetime
from uuid import uuid4

import pytest

from app.domain.ai_analysis.entities import AIAnalysis
from app.domain.ai_analysis.enums import AnalysisQualityTier, AnalysisStatus


@pytest.mark.asyncio
async def test_get_candidate_analyses_returns_list(ai_client, auth_headers_for, fake_analysis_repo):
    candidate_id = uuid4()
    await fake_analysis_repo.save(
        AIAnalysis(
            id=uuid4(),
            candidate_id=candidate_id,
            job_posting_id=uuid4(),
            status=AnalysisStatus.PENDING,
            match_score=None,
            quality_tier=AnalysisQualityTier.FAST,
            tokens_consumed=0,
            created_at=datetime.now(UTC),
            completed_at=None,
        )
    )

    response = await ai_client.get(
        f"/api/v1/candidates/{candidate_id}/analyses/",
        headers=auth_headers_for(candidate_id),
    )

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["candidate_id"] == str(candidate_id)


@pytest.mark.asyncio
async def test_post_candidate_index_stores_embedding(
    ai_client,
    auth_headers_for,
    candidate_profile_factory,
    fake_vector_store,
):
    candidate_id = uuid4()
    await candidate_profile_factory(candidate_id)

    response = await ai_client.post(
        f"/api/v1/candidates/{candidate_id}/index",
        headers=auth_headers_for(candidate_id),
    )

    assert response.status_code == 202
    assert response.json() == {"message": "indexing started"}
    assert await fake_vector_store.get_candidate(candidate_id) is not None


@pytest.mark.asyncio
async def test_get_candidate_job_matches_returns_ranked_jobs(
    ai_client,
    auth_headers_for,
    fake_vector_store,
):
    candidate_id = uuid4()
    best_job_id = uuid4()
    other_job_id = uuid4()
    await fake_vector_store.upsert_candidate(candidate_id, [1.0, 0.0], {"kind": "candidate"})
    await fake_vector_store.upsert_job(best_job_id, [1.0, 0.0], {"title": "Backend Engineer"})
    await fake_vector_store.upsert_job(other_job_id, [0.0, 1.0], {"title": "Frontend Engineer"})

    response = await ai_client.get(
        f"/api/v1/candidates/{candidate_id}/job-matches/?top_k=2",
        headers=auth_headers_for(candidate_id),
    )

    assert response.status_code == 200
    data = response.json()
    assert [item["id"] for item in data] == [str(best_job_id), str(other_job_id)]
    assert data[0]["metadata"]["title"] == "Backend Engineer"


@pytest.mark.asyncio
async def test_get_candidate_job_matches_returns_404_when_candidate_not_indexed(ai_client, auth_headers_for):
    candidate_id = uuid4()

    response = await ai_client.get(
        f"/api/v1/candidates/{candidate_id}/job-matches/",
        headers=auth_headers_for(candidate_id),
    )

    assert response.status_code == 404
    assert response.json()["code"] == "candidate_embedding_not_found"
