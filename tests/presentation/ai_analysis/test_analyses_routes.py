from datetime import UTC, datetime
from uuid import uuid4

import pytest

from app.domain.ai_analysis.entities import AIAnalysis
from app.domain.ai_analysis.enums import AnalysisQualityTier, AnalysisStatus
from app.domain.ai_analysis.value_objects import MatchScore


def _analysis(candidate_id, job_posting_id, status: AnalysisStatus) -> AIAnalysis:
    score = None
    completed_at = None
    if status == AnalysisStatus.COMPLETED:
        score = MatchScore(
            overall=0.91,
            skills_score=0.9,
            experience_score=0.92,
            location_score=0.95,
            salary_score=0.87,
            explanation="Strong match.",
        )
        completed_at = datetime.now(UTC)

    return AIAnalysis(
        id=uuid4(),
        candidate_id=candidate_id,
        job_posting_id=job_posting_id,
        status=status,
        match_score=score,
        quality_tier=AnalysisQualityTier.FAST,
        tokens_consumed=42,
        created_at=datetime.now(UTC),
        completed_at=completed_at,
    )


@pytest.mark.asyncio
async def test_post_analyses_returns_completed_match(ai_client, auth_headers_for):
    candidate_id = uuid4()
    job_posting_id = uuid4()

    response = await ai_client.post(
        "/api/v1/analyses/",
        headers=auth_headers_for(candidate_id),
        json={"candidate_id": str(candidate_id), "job_posting_id": str(job_posting_id)},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["candidate_id"] == str(candidate_id)
    assert data["job_posting_id"] == str(job_posting_id)
    assert data["status"] == "completed"
    assert data["match_score"]["overall"] == 0.75
    assert response.headers["location"] == f"/api/v1/analyses/{data['id']}"


@pytest.mark.asyncio
async def test_post_analyses_returns_202_for_pending_existing_analysis(
    ai_client,
    auth_headers_for,
    fake_analysis_repo,
):
    candidate_id = uuid4()
    job_posting_id = uuid4()
    pending = _analysis(candidate_id, job_posting_id, AnalysisStatus.PENDING)
    await fake_analysis_repo.save(pending)

    response = await ai_client.post(
        "/api/v1/analyses/",
        headers=auth_headers_for(candidate_id),
        json={"candidate_id": str(candidate_id), "job_posting_id": str(job_posting_id)},
    )

    assert response.status_code == 202
    assert response.json()["status"] == "pending"
    assert response.headers["location"] == f"/api/v1/analyses/{pending.id}"


@pytest.mark.asyncio
async def test_get_analysis_returns_analysis(ai_client, auth_headers_for, fake_analysis_repo):
    candidate_id = uuid4()
    analysis = _analysis(candidate_id, uuid4(), AnalysisStatus.COMPLETED)
    await fake_analysis_repo.save(analysis)

    response = await ai_client.get(
        f"/api/v1/analyses/{analysis.id}",
        headers=auth_headers_for(candidate_id),
    )

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(analysis.id)
    assert data["match_score"]["explanation"] == "Strong match."


@pytest.mark.asyncio
async def test_get_analysis_returns_404_when_missing(ai_client, auth_headers_for):
    response = await ai_client.get(
        f"/api/v1/analyses/{uuid4()}",
        headers=auth_headers_for(uuid4()),
    )

    assert response.status_code == 404
    assert response.json()["code"] == "ai_analysis_not_found"


@pytest.mark.asyncio
async def test_post_analyses_requires_authentication(ai_client):
    response = await ai_client.post(
        "/api/v1/analyses/",
        json={"candidate_id": str(uuid4()), "job_posting_id": str(uuid4())},
    )

    assert response.status_code == 401
    assert response.json()["code"] == "invalid_authentication"
