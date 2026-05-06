# tests/application/job_search/test_search_jobs_use_case.py
import pytest

from app.application.job_search.use_cases import SearchJobsUseCase
from tests.fakes.job_search.fake_job_scraper_gateway import (
    FakeJobScraperGateway,
    make_scraped_job,
)


class FakeJobPostingRepository:
    """In-memory fake for JobPostingRepository."""

    def __init__(self) -> None:
        self.upserted: list = []

    async def upsert(self, job):
        self.upserted.append(job)
        return job

    async def get_by_external_id(self, external_id, source):
        return next(
            (j for j in self.upserted
             if j.external_id == external_id and j.source == source),
            None,
        )

    async def list_by_candidate(self, candidate_id, limit=50, offset=0):
        return self.upserted[:limit]

    async def count_new_since_last_search(self, candidate_id):
        return 0


@pytest.mark.asyncio
async def test_search_jobs_returns_results_and_persists():
    jobs = [
        make_scraped_job(job_id="001", title="Python Dev"),
        make_scraped_job(job_id="002", title="Backend Engineer"),
    ]
    repo = FakeJobPostingRepository()
    use_case = SearchJobsUseCase(
        scraper=FakeJobScraperGateway(jobs=jobs),
        job_posting_repo=repo,
    )

    result = await use_case.execute(keywords="Python", location="Geneva")

    assert result.total == 2
    assert result.has_results is True
    assert len(repo.upserted) == 2  # ← persistance vérifiée


@pytest.mark.asyncio
async def test_search_jobs_passes_correct_query_to_gateway():
    gateway = FakeJobScraperGateway(jobs=[])
    use_case = SearchJobsUseCase(
        scraper=gateway,
        job_posting_repo=FakeJobPostingRepository(),
    )

    await use_case.execute(
        keywords="FastAPI",
        location="Zurich",
        limit=10,
        remote_only=True,
    )

    assert len(gateway.search_calls) == 1
    query = gateway.search_calls[0]
    assert query.keywords == "FastAPI"
    assert query.limit == 10
    assert query.remote_only is True


@pytest.mark.asyncio
async def test_search_jobs_returns_empty_when_no_results():
    repo = FakeJobPostingRepository()
    use_case = SearchJobsUseCase(
        scraper=FakeJobScraperGateway(jobs=[]),
        job_posting_repo=repo,
    )

    result = await use_case.execute(keywords="Cobol", location="Moon")

    assert result.total == 0
    assert result.has_results is False
    assert result.source == "unknown"
    assert len(repo.upserted) == 0


@pytest.mark.asyncio
async def test_get_job_detail_returns_matching_job():
    job = make_scraped_job(job_id="detail_001", title="Staff Engineer")
    gateway = FakeJobScraperGateway(jobs=[job])
    use_case = SearchJobsUseCase(
        scraper=gateway,
        job_posting_repo=FakeJobPostingRepository(),
    )

    result = await use_case.get_detail(job_id="detail_001")

    assert result is not None
    assert result.title == "Staff Engineer"
