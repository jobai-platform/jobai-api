import pytest
from uuid import uuid4

from app.application.job_search.search_agent_use_cases import (
    CreateSearchAgentCommand,
    CreateSearchAgentUseCase,
    DeleteSearchAgentUseCase,
    GetSearchAgentUseCase,
    RunSearchAgentUseCase,
    UpdateSearchAgentCommand,
    UpdateSearchAgentUseCase,
)
from app.application.job_search.use_cases import SearchJobsUseCase
from app.domain.common.exceptions import ConflictError, NotFoundError
from app.domain.job_search.search_agent import SearchAgent
from tests.fakes.job_search.fake_job_scraper_gateway import (
    FakeJobScraperGateway,
    FakeJobPostingRepository,
    make_scraped_job,
)
from tests.fakes.job_search.in_memory_search_agent_repo import InMemorySearchAgentRepository


def _make_agent_repo() -> InMemorySearchAgentRepository:
    return InMemorySearchAgentRepository()


def _make_create_uc(repo=None) -> tuple[CreateSearchAgentUseCase, InMemorySearchAgentRepository]:
    repo = repo or _make_agent_repo()
    return CreateSearchAgentUseCase(repo), repo


# ---------------------------------------------------------------------------
# CreateSearchAgentUseCase
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_create_search_agent_happy_path():
    uc, repo = _make_create_uc()
    candidate_id = uuid4()

    agent = await uc.execute(CreateSearchAgentCommand(
        candidate_id=candidate_id,
        keywords="python developer",
        location="Zurich",
    ))

    assert agent.id is not None
    assert agent.candidate_id == candidate_id
    assert agent.keywords == "python developer"
    assert agent.location == "Zurich"
    assert agent.is_active is True
    assert agent.last_run_at is None


@pytest.mark.asyncio
async def test_create_search_agent_defaults():
    uc, _ = _make_create_uc()

    agent = await uc.execute(CreateSearchAgentCommand(
        candidate_id=uuid4(),
        keywords="backend engineer",
        location="Geneva",
    ))

    assert agent.remote_only is False
    assert agent.date_posted_within_days == 7
    assert agent.limit == 25


@pytest.mark.asyncio
async def test_create_search_agent_with_custom_params():
    uc, _ = _make_create_uc()

    agent = await uc.execute(CreateSearchAgentCommand(
        candidate_id=uuid4(),
        keywords="data engineer",
        location="Basel",
        remote_only=True,
        date_posted_within_days=14,
        limit=50,
    ))

    assert agent.remote_only is True
    assert agent.date_posted_within_days == 14
    assert agent.limit == 50


@pytest.mark.asyncio
async def test_create_search_agent_raises_conflict_when_exists():
    uc, repo = _make_create_uc()
    candidate_id = uuid4()

    await uc.execute(CreateSearchAgentCommand(
        candidate_id=candidate_id,
        keywords="python",
        location="Zurich",
    ))

    with pytest.raises(ConflictError, match="search_agent_already_exists"):
        await uc.execute(CreateSearchAgentCommand(
            candidate_id=candidate_id,
            keywords="java",
            location="Bern",
        ))


# ---------------------------------------------------------------------------
# GetSearchAgentUseCase
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_search_agent_returns_existing():
    repo = _make_agent_repo()
    candidate_id = uuid4()
    from uuid import uuid4 as _uuid4
    agent = SearchAgent(
        id=_uuid4(),
        candidate_id=candidate_id,
        keywords="python",
        location="Zurich",
    )
    await repo.save(agent)

    result = await GetSearchAgentUseCase(repo).execute(candidate_id)

    assert result is not None
    assert result.keywords == "python"


@pytest.mark.asyncio
async def test_get_search_agent_returns_none_when_not_found():
    repo = _make_agent_repo()
    result = await GetSearchAgentUseCase(repo).execute(uuid4())
    assert result is None


# ---------------------------------------------------------------------------
# UpdateSearchAgentUseCase
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_update_search_agent_happy_path():
    create_uc, repo = _make_create_uc()
    agent = await create_uc.execute(CreateSearchAgentCommand(
        candidate_id=uuid4(),
        keywords="python",
        location="Zurich",
    ))

    updated = await UpdateSearchAgentUseCase(repo).execute(UpdateSearchAgentCommand(
        agent_id=agent.id,
        keywords="data engineer",
        limit=50,
    ))

    assert updated.keywords == "data engineer"
    assert updated.limit == 50
    assert updated.location == "Zurich"


@pytest.mark.asyncio
async def test_update_search_agent_raises_not_found():
    repo = _make_agent_repo()

    with pytest.raises(NotFoundError, match="search_agent_not_found"):
        await UpdateSearchAgentUseCase(repo).execute(UpdateSearchAgentCommand(
            agent_id=uuid4(),
            keywords="python",
        ))


@pytest.mark.asyncio
async def test_update_search_agent_raises_on_invalid_limit():
    create_uc, repo = _make_create_uc()
    agent = await create_uc.execute(CreateSearchAgentCommand(
        candidate_id=uuid4(),
        keywords="python",
        location="Zurich",
    ))

    with pytest.raises(ValueError, match="limit must be between 1 and 100"):
        await UpdateSearchAgentUseCase(repo).execute(UpdateSearchAgentCommand(
            agent_id=agent.id,
            limit=999,
        ))


# ---------------------------------------------------------------------------
# DeleteSearchAgentUseCase
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_delete_search_agent_happy_path():
    create_uc, repo = _make_create_uc()
    candidate_id = uuid4()
    agent = await create_uc.execute(CreateSearchAgentCommand(
        candidate_id=candidate_id,
        keywords="python",
        location="Zurich",
    ))

    await DeleteSearchAgentUseCase(repo).execute(agent.id)

    assert await repo.get_by_id(agent.id) is None
    assert await repo.get_by_candidate_id(candidate_id) is None


@pytest.mark.asyncio
async def test_delete_search_agent_raises_not_found():
    repo = _make_agent_repo()

    with pytest.raises(NotFoundError, match="search_agent_not_found"):
        await DeleteSearchAgentUseCase(repo).execute(uuid4())


# ---------------------------------------------------------------------------
# RunSearchAgentUseCase
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_run_search_agent_marks_ran_and_persists():
    create_uc, agent_repo = _make_create_uc()
    candidate_id = uuid4()
    agent = await create_uc.execute(CreateSearchAgentCommand(
        candidate_id=candidate_id,
        keywords="python developer",
        location="Zurich",
        limit=10,
    ))
    assert agent.last_run_at is None

    scraper = FakeJobScraperGateway(jobs=[make_scraped_job()])
    job_repo = FakeJobPostingRepository()
    search_uc = SearchJobsUseCase(scraper=scraper, job_posting_repo=job_repo)
    run_uc = RunSearchAgentUseCase(agent_repo=agent_repo, search_jobs_use_case=search_uc)

    result = await run_uc.execute(agent.id)

    assert result.agent.last_run_at is not None
    assert result.jobs_found == 1
    assert len(scraper.search_calls) == 1
    query = scraper.search_calls[0]
    assert query.keywords == "python developer"
    assert query.location == "Zurich"
    assert query.limit == 10


@pytest.mark.asyncio
async def test_run_search_agent_passes_agent_params_to_scraper():
    create_uc, agent_repo = _make_create_uc()
    agent = await create_uc.execute(CreateSearchAgentCommand(
        candidate_id=uuid4(),
        keywords="data scientist",
        location="Basel",
        remote_only=True,
        date_posted_within_days=14,
        limit=5,
    ))

    scraper = FakeJobScraperGateway(jobs=[])
    job_repo = FakeJobPostingRepository()
    search_uc = SearchJobsUseCase(scraper=scraper, job_posting_repo=job_repo)
    run_uc = RunSearchAgentUseCase(agent_repo=agent_repo, search_jobs_use_case=search_uc)

    result = await run_uc.execute(agent.id)

    query = scraper.search_calls[0]
    assert query.remote_only is True
    assert query.date_posted_within_days == 14
    assert query.limit == 5
    assert result.jobs_found == 0


@pytest.mark.asyncio
async def test_run_search_agent_raises_not_found():
    agent_repo = _make_agent_repo()
    scraper = FakeJobScraperGateway(jobs=[])
    job_repo = FakeJobPostingRepository()
    search_uc = SearchJobsUseCase(scraper=scraper, job_posting_repo=job_repo)
    run_uc = RunSearchAgentUseCase(agent_repo=agent_repo, search_jobs_use_case=search_uc)

    with pytest.raises(NotFoundError, match="search_agent_not_found"):
        await run_uc.execute(uuid4())
