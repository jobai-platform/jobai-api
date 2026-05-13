import pytest
import pytest_asyncio
import uuid
from datetime import datetime, UTC

from app.domain.ai_analysis.entities import AIAnalysis
from app.domain.ai_analysis.enums import AnalysisStatus, AnalysisQualityTier
from app.infrastructure.persistence.repositories.ai_analysis_sqlalchemy import SQLAlchemyAIAnalysisRepository
from app.infrastructure.persistence.models.candidate_profile import CandidateProfileModel
from app.infrastructure.persistence.models.job_posting import JobPostingModel
from app.infrastructure.persistence.models.user import UserModel


@pytest_asyncio.fixture
async def seeded_candidate_and_job(db_session):
    """Seed a user, candidate_profile, and job_posting to satisfy FK constraints."""
    user = UserModel(
        email=f"aitest-{uuid.uuid4().hex[:8]}@example.com",
        username=f"aitest-{uuid.uuid4().hex[:8]}",
        hashed_password="fakehashed",
        role="user",
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()

    candidate = CandidateProfileModel(id=uuid.uuid4(), user_id=user.id)
    db_session.add(candidate)
    await db_session.flush()

    job = JobPostingModel(
        id=uuid.uuid4(),
        external_id=uuid.uuid4().hex,
        source="test",
        title="Test Job",
        company="Acme Corp",
        location="Remote",
        description="A test job for integration tests.",
        url="https://example.com/job/1",
    )
    db_session.add(job)
    await db_session.flush()

    return candidate.id, job.id


@pytest.mark.integration
@pytest.mark.asyncio
async def test_save_and_find_by_id(db_session, seeded_candidate_and_job):
    """GIVEN a new AIAnalysis entity
    WHEN saved and retrieved by id
    THEN the retrieved entity matches the original
    """
    candidate_id, job_posting_id = seeded_candidate_and_job
    repo = SQLAlchemyAIAnalysisRepository(session=db_session)
    analysis = AIAnalysis(
        id=uuid.uuid4(),
        candidate_id=candidate_id,
        job_posting_id=job_posting_id,
        status=AnalysisStatus.PENDING,
        match_score=None,
        quality_tier=AnalysisQualityTier.FAST,
        tokens_consumed=0,
        created_at=datetime.now(UTC),
        completed_at=None,
    )

    await repo.save(analysis)
    retrieved = await repo.find_by_id(analysis.id)

    assert retrieved is not None
    assert retrieved.id == analysis.id
    assert retrieved.status == AnalysisStatus.PENDING


@pytest.mark.integration
@pytest.mark.asyncio
async def test_find_by_candidate_and_job(db_session, seeded_candidate_and_job):
    """GIVEN an analysis saved for candidate/job pair
    WHEN find_by_candidate_and_job is called
    THEN the analysis is returned
    """
    candidate_id, job_posting_id = seeded_candidate_and_job
    repo = SQLAlchemyAIAnalysisRepository(session=db_session)

    analysis = AIAnalysis(
        id=uuid.uuid4(),
        candidate_id=candidate_id,
        job_posting_id=job_posting_id,
        status=AnalysisStatus.PENDING,
        match_score=None,
        quality_tier=AnalysisQualityTier.BALANCED,
        tokens_consumed=0,
        created_at=datetime.now(UTC),
        completed_at=None,
    )
    await repo.save(analysis)

    found = await repo.find_by_candidate_and_job(candidate_id, job_posting_id)
    assert found is not None
    assert found.candidate_id == candidate_id
