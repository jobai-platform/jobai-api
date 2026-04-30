import pytest
from datetime import date

from app.domain.job_search.value_objects import ScrapedJob, JobSearchQuery


def test_scraped_job_is_immutable():
    job = ScrapedJob(
        job_id="001",
        title="Backend Engineer",
        company="JobAI",
        location="Geneva",
        description="Great role",
        url="https://linkedin.com/jobs/001",
        source="linkedin",
    )
    with pytest.raises(Exception):
        job.title = "Modified"  # type: ignore[misc]


def test_scraped_job_optional_fields_default_to_none():
    job = ScrapedJob(
        job_id="002",
        title="Dev",
        company="Corp",
        location="Zurich",
        description="...",
        url="https://example.com",
        source="indeed",
    )
    assert job.apply_url is None
    assert job.posted_at is None
    assert job.is_remote is None
    assert job.job_type is None
    assert job.insights is None
    assert job.skills == tuple()


def test_scraped_job_skills_stored_as_tuple():
    job = ScrapedJob(
        job_id="003",
        title="ML Engineer",
        company="AI Corp",
        location="Basel",
        description="...",
        url="https://example.com",
        source="linkedin",
        skills=("Python", "PyTorch", "FastAPI"),
    )
    assert isinstance(job.skills, tuple)
    assert "Python" in job.skills


def test_job_search_query_defaults():
    query = JobSearchQuery(keywords="Python", location="Geneva")
    assert query.limit == 25
    assert query.remote_only is False
    assert query.date_posted_within_days == 7


def test_job_search_query_is_immutable():
    query = JobSearchQuery(keywords="Python", location="Geneva")
    with pytest.raises(Exception):
        query.keywords = "Java"  # type: ignore[misc]


def test_job_search_query_custom_values():
    query = JobSearchQuery(
        keywords="FastAPI",
        location="Zurich",
        limit=10,
        remote_only=True,
        date_posted_within_days=1,
    )
    assert query.limit == 10
    assert query.remote_only is True
    assert query.date_posted_within_days == 1
