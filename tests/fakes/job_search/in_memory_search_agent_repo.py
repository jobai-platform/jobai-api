from typing import Optional
from uuid import UUID

from app.application.job_search.ports import SearchAgentRepository
from app.domain.job_search.search_agent import SearchAgent


class InMemorySearchAgentRepository(SearchAgentRepository):
    def __init__(self) -> None:
        self._store: dict[UUID, SearchAgent] = {}

    async def save(self, agent: SearchAgent) -> SearchAgent:
        self._store[agent.id] = agent
        return agent

    async def get_by_id(self, agent_id: UUID) -> Optional[SearchAgent]:
        return self._store.get(agent_id)

    async def get_by_candidate_id(self, candidate_id: UUID) -> Optional[SearchAgent]:
        return next(
            (a for a in self._store.values() if a.candidate_id == candidate_id),
            None,
        )

    async def list_by_candidate(self, candidate_id: UUID) -> list[SearchAgent]:
        return [a for a in self._store.values() if a.candidate_id == candidate_id]

    async def delete(self, agent_id: UUID) -> None:
        self._store.pop(agent_id, None)
