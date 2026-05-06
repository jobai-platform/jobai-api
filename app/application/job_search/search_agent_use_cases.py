from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional
from uuid import UUID, uuid4

from app.application.job_search.dto import JobSearchResult

from app.application.job_search.ports import SearchAgentRepository
from app.application.job_search.use_cases import SearchJobsUseCase
from app.domain.common.exceptions import ConflictError, NotFoundError
from app.domain.job_search.search_agent import SearchAgent

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class CreateSearchAgentCommand:
    candidate_id: UUID
    keywords: str
    location: str
    remote_only: bool = False
    date_posted_within_days: int = 7
    limit: int = 25
    easy_apply_only: bool | None = None


@dataclass(frozen=True)
class RunSearchAgentResult:
    agent: SearchAgent
    jobs_found: int


@dataclass(frozen=True)
class UpdateSearchAgentCommand:
    agent_id: UUID
    keywords: str | None = None
    location: str | None = None
    remote_only: bool | None = None
    date_posted_within_days: int | None = None
    limit: int | None = None
    easy_apply_only: bool | None = None


class CreateSearchAgentUseCase:
    """Create a new SearchAgent for a candidate. One active agent per candidate."""

    def __init__(self, repo: SearchAgentRepository) -> None:
        self._repo = repo

    async def execute(self, command: CreateSearchAgentCommand) -> SearchAgent:
        existing = await self._repo.get_by_candidate_id(command.candidate_id)
        if existing:
            raise ConflictError(
                code="search_agent_already_exists",
                details="Candidate already has a search agent. Update or delete it first.",
            )
        agent = SearchAgent(
            id=uuid4(),
            candidate_id=command.candidate_id,
            keywords=command.keywords,
            location=command.location,
            remote_only=command.remote_only,
            date_posted_within_days=command.date_posted_within_days,
            limit=command.limit,
            easy_apply_only=command.easy_apply_only,
        )
        return await self._repo.save(agent)


class GetSearchAgentUseCase:
    """Retrieve the SearchAgent for a candidate."""

    def __init__(self, repo: SearchAgentRepository) -> None:
        self._repo = repo

    async def execute(self, candidate_id: UUID) -> Optional[SearchAgent]:
        return await self._repo.get_by_candidate_id(candidate_id)


class UpdateSearchAgentUseCase:
    """Update an existing SearchAgent."""

    def __init__(self, repo: SearchAgentRepository) -> None:
        self._repo = repo

    async def execute(self, command: UpdateSearchAgentCommand) -> SearchAgent:
        agent = await self._repo.get_by_id(command.agent_id)
        if not agent:
            raise NotFoundError(
                code="search_agent_not_found",
                details=f"SearchAgent {command.agent_id} not found.",
            )
        agent.update(
            keywords=command.keywords,
            location=command.location,
            remote_only=command.remote_only,
            date_posted_within_days=command.date_posted_within_days,
            limit=command.limit,
            easy_apply_only=command.easy_apply_only,
        )
        return await self._repo.save(agent)


class DeleteSearchAgentUseCase:
    """Delete a SearchAgent by ID."""

    def __init__(self, repo: SearchAgentRepository) -> None:
        self._repo = repo

    async def execute(self, agent_id: UUID) -> None:
        agent = await self._repo.get_by_id(agent_id)
        if not agent:
            raise NotFoundError(
                code="search_agent_not_found",
                details=f"SearchAgent {agent_id} not found.",
            )
        await self._repo.delete(agent_id)


class RunSearchAgentUseCase:
    """Trigger a SearchAgent: scrape jobs and persist deduplicated results."""

    def __init__(
        self,
        agent_repo: SearchAgentRepository,
        search_jobs_use_case: SearchJobsUseCase,
    ) -> None:
        self._agent_repo = agent_repo
        self._search_jobs_use_case = search_jobs_use_case

    async def execute(self, agent_id: UUID) -> RunSearchAgentResult:
        agent = await self._agent_repo.get_by_id(agent_id)
        if not agent:
            raise NotFoundError(
                code="search_agent_not_found",
                details=f"SearchAgent {agent_id} not found.",
            )

        logger.info(
            "RunSearchAgentUseCase: running agent=%s keywords=%r location=%r",
            agent_id,
            agent.keywords,
            agent.location,
        )

        result = await self._search_jobs_use_case.execute(
            keywords=agent.keywords,
            location=agent.location,
            limit=agent.limit,
            remote_only=agent.remote_only,
            date_posted_within_days=agent.date_posted_within_days,
            easy_apply_only=agent.easy_apply_only,
        )

        logger.info(
            "RunSearchAgentUseCase: agent=%s found %d jobs",
            agent_id,
            result.total,
        )

        agent.mark_ran()
        saved_agent = await self._agent_repo.save(agent)
        return RunSearchAgentResult(agent=saved_agent, jobs_found=result.total)
