import pytest

from app.application.job_search.use_cases import SearchJobsUseCase
from tests.fakes.job_search.fake_job_scraper_gateway import (
    FakeJobScraperGateway,
    make_scraped_job,
)


@pytest.mark.asyncio
async def test_search_jobs_returns_results():
    jobs = [
        make_scraped_job(job_id="001", title="Python Dev"),
        make_scraped_job(job_id="002", title="Backend Engineer"),
    ]
    use_case = SearchJobsUseCase(scraper=FakeJobScraperGateway(jobs=jobs))

    result = await use_case.execute(keywords="Python", location="Geneva")

    assert result.total == 2
    assert result.has_results is True
    assert result.keywords == "Python"
    assert result.location == "Geneva"
    assert result.source == "linkedin"


@pytest.mark.asyncio
async def test_search_jobs_passes_correct_query_to_gateway():
    gateway = FakeJobScraperGateway(jobs=[])
    use_case = SearchJobsUseCase(scraper=gateway)

    await use_case.execute(
        keywords="FastAPI",
        location="Zurich",
        limit=10,
        remote_only=True,
    )

    assert len(gateway.search_calls) == 1
    query = gateway.search_calls[0]
    assert query.keywords == "FastAPI"
    assert query.location == "Zurich"
    assert query.limit == 10
    assert query.remote_only is True


@pytest.mark.asyncio
async def test_search_jobs_returns_empty_result_when_no_jobs():
    use_case = SearchJobsUseCase(scraper=FakeJobScraperGateway(jobs=[]))

    result = await use_case.execute(keywords="Cobol", location="Moon")

    assert result.total == 0
    assert result.has_results is False
    assert result.jobs == []
    assert result.source == "unknown"


@pytest.mark.asyncio
async def test_get_job_detail_returns_matching_job():
    job = make_scraped_job(job_id="detail_001", title="Staff Engineer")
    gateway = FakeJobScraperGateway(jobs=[job])
    use_case = SearchJobsUseCase(scraper=gateway)

    result = await use_case.get_detail(job_id="detail_001")

    assert result is not None
    assert result.title == "Staff Engineer"
    assert gateway.detail_calls == ["detail_001"]


@pytest.mark.asyncio
async def test_get_job_detail_returns_none_when_not_found():
    use_case = SearchJobsUseCase(scraper=FakeJobScraperGateway(jobs=[]))

    result = await use_case.get_detail(job_id="ghost_999")

    assert result is None
