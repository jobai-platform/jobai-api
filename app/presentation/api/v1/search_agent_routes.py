import logging
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status
from fastapi.responses import Response

from app.application.job_search.search_agent_use_cases import (
    CreateSearchAgentCommand,
    UpdateSearchAgentCommand,
)
from app.core.dependency import (
    CreateSearchAgentDep,
    DeleteSearchAgentDep,
    GetSearchAgentDep,
    RunSearchAgentDep,
    UpdateSearchAgentDep,
)
from app.domain.job_search.search_agent import SearchAgent
from app.presentation.api.v1.schemas.job_search import (
    RunSearchAgentResponse,
    SearchAgentCreateRequest,
    SearchAgentResponse,
    SearchAgentUpdateRequest,
)
from app.presentation.security.deps import get_current_user_id

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/search-agents", tags=["Search Agents"])

CurrentUserIdDep = Annotated[UUID, Depends(get_current_user_id)]


def _to_response(agent: SearchAgent) -> SearchAgentResponse:
    return SearchAgentResponse(
        id=agent.id,
        candidate_id=agent.candidate_id,
        keywords=agent.keywords,
        location=agent.location,
        remote_only=agent.remote_only,
        date_posted_within_days=agent.date_posted_within_days,
        limit=agent.limit,
        easy_apply_only=agent.easy_apply_only,
        is_active=agent.is_active,
        last_run_at=agent.last_run_at,
        created_at=agent.created_at,
        updated_at=agent.updated_at,
    )


@router.post(
    "",
    response_model=SearchAgentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a search agent",
    responses={
        201: {"description": "Search agent created"},
        401: {"description": "Authentication required"},
        409: {"description": "Agent already exists for candidate"},
        422: {"description": "Validation error"},
    },
)
async def create_search_agent(
    body: SearchAgentCreateRequest,
    current_user_id: CurrentUserIdDep,
    use_case: CreateSearchAgentDep,
) -> SearchAgentResponse:
    agent = await use_case.execute(CreateSearchAgentCommand(
        candidate_id=current_user_id,
        keywords=body.keywords,
        location=body.location,
        remote_only=body.remote_only,
        date_posted_within_days=body.date_posted_within_days,
        limit=body.limit,
        easy_apply_only=body.easy_apply_only,
    ))
    return _to_response(agent)


@router.get(
    "/me",
    response_model=SearchAgentResponse | None,
    status_code=status.HTTP_200_OK,
    summary="Get my search agent",
    responses={
        200: {"description": "Search agent or null"},
        401: {"description": "Authentication required"},
    },
)
async def get_my_search_agent(
    current_user_id: CurrentUserIdDep,
    use_case: GetSearchAgentDep,
) -> SearchAgentResponse | None:
    agent = await use_case.execute(current_user_id)
    return _to_response(agent) if agent else None


@router.put(
    "/{agent_id}",
    response_model=SearchAgentResponse,
    status_code=status.HTTP_200_OK,
    summary="Update a search agent",
    responses={
        200: {"description": "Search agent updated"},
        401: {"description": "Authentication required"},
        404: {"description": "Search agent not found"},
        422: {"description": "Validation error"},
    },
)
async def update_search_agent(
    agent_id: UUID,
    body: SearchAgentUpdateRequest,
    _current_user_id: CurrentUserIdDep,
    use_case: UpdateSearchAgentDep,
) -> SearchAgentResponse:
    agent = await use_case.execute(UpdateSearchAgentCommand(
        agent_id=agent_id,
        keywords=body.keywords,
        location=body.location,
        remote_only=body.remote_only,
        date_posted_within_days=body.date_posted_within_days,
        limit=body.limit,
        easy_apply_only=body.easy_apply_only,
    ))
    return _to_response(agent)


@router.delete(
    "/{agent_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a search agent",
    responses={
        204: {"description": "Search agent deleted"},
        401: {"description": "Authentication required"},
        404: {"description": "Search agent not found"},
    },
)
async def delete_search_agent(
    agent_id: UUID,
    _current_user_id: CurrentUserIdDep,
    use_case: DeleteSearchAgentDep,
) -> Response:
    await use_case.execute(agent_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/{agent_id}/run",
    response_model=RunSearchAgentResponse,
    status_code=status.HTTP_200_OK,
    summary="Run a search agent",
    responses={
        200: {"description": "Agent ran — returns agent state + jobs_found count"},
        401: {"description": "Authentication required"},
        404: {"description": "Search agent not found"},
        502: {"description": "Scraper unavailable"},
    },
)
async def run_search_agent(
    agent_id: UUID,
    _current_user_id: CurrentUserIdDep,
    use_case: RunSearchAgentDep,
) -> RunSearchAgentResponse:
    result = await use_case.execute(agent_id)
    return RunSearchAgentResponse(
        agent=_to_response(result.agent),
        jobs_found=result.jobs_found,
    )
