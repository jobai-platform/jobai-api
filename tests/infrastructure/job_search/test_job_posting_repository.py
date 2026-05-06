import pytest
from datetime import date

from app.domain.job_search.entities import JobPosting
from app.infrastructure.persistence.repositories.job_posting_sqlalchemy import (
    JobPostingSQLAlchemyRepository,
)


def make_job_posting(**kwargs) -> JobPosting:
    defaults = {
        "external_id": "li_test_001",
        "source": "linkedin",
        "title": "Senior Python Developer",
        "company": "Acme Corp",
        "location": "Geneva, Switzerland",
        "description": "We are looking for a senior Python developer.",
        "url": "https://linkedin.com/jobs/view/li_test_001",
        "posted_at": date(2026, 4, 28),
        "is_remote": False,
        "job_type": "fulltime",
        "skills": ("Python", "FastAPI", "PostgreSQL"),
    }
    return JobPosting(**{**defaults, **kwargs})


@pytest.mark.asyncio
async def test_upsert_creates_job_posting(db_session):
    repo = JobPostingSQLAlchemyRepository(session=db_session)
    job = make_job_posting()

    saved = await repo.upsert(job)

    assert saved.id is not None
    assert saved.external_id == "li_test_001"
    assert saved.source == "linkedin"
    assert saved.title == "Senior Python Developer"
    assert saved.skills == ("Python", "FastAPI", "PostgreSQL")


@pytest.mark.asyncio
async def test_upsert_updates_existing_job_posting(db_session):
    repo = JobPostingSQLAlchemyRepository(session=db_session)
    job = make_job_posting()
    await repo.upsert(job)

    # Même external_id + source → update
    updated_job = make_job_posting(
        title="Lead Python Developer",   # titre mis à jour
        insights="100 applicants",
    )
    saved = await repo.upsert(updated_job)

    assert saved.title == "Lead Python Developer"
    assert saved.insights == "100 applicants"


@pytest.mark.asyncio
async def test_get_by_external_id_returns_job(db_session):
    repo = JobPostingSQLAlchemyRepository(session=db_session)
    job = make_job_posting()
    await repo.upsert(job)

    found = await repo.get_by_external_id("li_test_001", "linkedin")

    assert found is not None
    assert found.external_id == "li_test_001"
    assert found.company == "Acme Corp"


@pytest.mark.asyncio
async def test_get_by_external_id_returns_none_when_not_found(db_session):
    repo = JobPostingSQLAlchemyRepository(session=db_session)

    result = await repo.get_by_external_id("ghost_999", "linkedin")

    assert result is None


@pytest.mark.asyncio
async def test_upsert_deduplication_same_external_id_different_source(db_session):
    """
    Même external_id mais source différente → deux entrées distinctes.
    """
    repo = JobPostingSQLAlchemyRepository(session=db_session)

    linkedin_job = make_job_posting(external_id="job_dup", source="linkedin")
    indeed_job = make_job_posting(external_id="job_dup", source="indeed")

    saved_li = await repo.upsert(linkedin_job)
    saved_in = await repo.upsert(indeed_job)

    assert saved_li.id != saved_in.id

    found_li = await repo.get_by_external_id("job_dup", "linkedin")
    found_in = await repo.get_by_external_id("job_dup", "indeed")

    assert found_li is not None
    assert found_in is not None
    assert found_li.id != found_in.id
