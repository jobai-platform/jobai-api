from __future__ import annotations

from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.job_search.ports import SearchAgentRepository
from app.domain.job_search.search_agent import SearchAgent
from app.infrastructure.persistence.models.search_agent import SearchAgentModel


class SQLAlchemySearchAgentRepository(SearchAgentRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, agent: SearchAgent) -> SearchAgent:
        result = await self._session.execute(
            select(SearchAgentModel).where(SearchAgentModel.id == agent.id)
        )
        model = result.scalar_one_or_none()

        if model is None:
            model = SearchAgentModel(id=agent.id, candidate_id=agent.candidate_id)
            self._session.add(model)

        model.keywords = agent.keywords
        model.location = agent.location
        model.remote_only = agent.remote_only
        model.date_posted_within_days = agent.date_posted_within_days
        model.limit = agent.limit
        model.easy_apply_only = agent.easy_apply_only
        model.is_active = agent.is_active
        model.last_run_at = agent.last_run_at

        # Flush to send any new INSERT or UPDATE to the database
        await self._session.flush([model])
        # Refresh to get any server-side defaults (like timestamps) that were set by the database
        await self._session.refresh(model)
        return _to_domain(model)

    async def get_by_id(self, agent_id: UUID) -> Optional[SearchAgent]:
        result = await self._session.execute(
            select(SearchAgentModel).where(SearchAgentModel.id == agent_id)
        )
        model = result.scalar_one_or_none()
        return _to_domain(model) if model else None

    async def get_by_candidate_id(self, candidate_id: UUID) -> Optional[SearchAgent]:
        result = await self._session.execute(
            select(SearchAgentModel).where(
                SearchAgentModel.candidate_id == candidate_id,
                SearchAgentModel.is_active.is_(True),
            )
        )
        model = result.scalar_one_or_none()
        return _to_domain(model) if model else None

    async def list_by_candidate(self, candidate_id: UUID) -> list[SearchAgent]:
        result = await self._session.execute(
            select(SearchAgentModel).where(SearchAgentModel.candidate_id == candidate_id)
        )
        return [_to_domain(m) for m in result.scalars().all()]

    async def delete(self, agent_id: UUID) -> None:
        result = await self._session.execute(
            select(SearchAgentModel).where(SearchAgentModel.id == agent_id)
        )
        model = result.scalar_one_or_none()
        if model:
            await self._session.delete(model)
            # Note: commit is handled at the outer layer (dependency)


def _to_domain(model: SearchAgentModel) -> SearchAgent:
    return SearchAgent(
        id=model.id,
        candidate_id=model.candidate_id,
        keywords=model.keywords,
        location=model.location,
        remote_only=model.remote_only,
        date_posted_within_days=model.date_posted_within_days,
        limit=model.limit,
        easy_apply_only=model.easy_apply_only,
        is_active=model.is_active,
        last_run_at=model.last_run_at,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )
