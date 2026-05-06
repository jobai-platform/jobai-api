import pytest
from unittest.mock import AsyncMock
from uuid import uuid4

from app.application.job_search.search_agent_use_cases import (
    CreateSearchAgentUseCase,
    DeleteSearchAgentUseCase,
    GetSearchAgentUseCase,
    RunSearchAgentUseCase,
    UpdateSearchAgentUseCase,
)
from app.core.dependency import (
    get_create_search_agent_use_case,
    get_delete_search_agent_use_case,
    get_get_search_agent_use_case,
    get_run_search_agent_use_case,
    get_update_search_agent_use_case,
)
from app.domain.common.exceptions import ConflictError, NotFoundError
from app.domain.job_search.search_agent import SearchAgent
from app.main import app


def _make_agent(**kwargs) -> SearchAgent:
    defaults = dict(
        id=uuid4(),
        candidate_id=uuid4(),
        keywords="python developer",
        location="Zurich",
    )
    return SearchAgent(**{**defaults, **kwargs})


# ---------------------------------------------------------------------------
# POST /search-agents
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_create_search_agent_returns_201(client, create_user_in_db, jwt_service):
    user = await create_user_in_db(email="agent_create@test.com", password="secret")
    token = jwt_service.create_access_token(
        subject=str(user.id),
        extra={"role": "user", "email": user.email},
    )

    fake_agent = _make_agent(candidate_id=user.id)
    fake_uc = AsyncMock(spec=CreateSearchAgentUseCase)
    fake_uc.execute.return_value = fake_agent
    app.dependency_overrides[get_create_search_agent_use_case] = lambda: fake_uc

    response = await client.post(
        "/api/v1/search-agents",
        headers={"Authorization": f"Bearer {token}"},
        json={"keywords": "python developer", "location": "Zurich"},
    )

    app.dependency_overrides.pop(get_create_search_agent_use_case, None)

    assert response.status_code == 201
    data = response.json()
    assert data["keywords"] == "python developer"
    assert data["location"] == "Zurich"
    assert data["is_active"] is True


@pytest.mark.asyncio
async def test_create_search_agent_returns_401_without_token(client):
    response = await client.post(
        "/api/v1/search-agents",
        json={"keywords": "python", "location": "Zurich"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_create_search_agent_returns_422_on_empty_keywords(client, create_user_in_db, jwt_service):
    user = await create_user_in_db(email="agent_422@test.com", password="secret")
    token = jwt_service.create_access_token(
        subject=str(user.id),
        extra={"role": "user", "email": user.email},
    )

    response = await client.post(
        "/api/v1/search-agents",
        headers={"Authorization": f"Bearer {token}"},
        json={"keywords": "", "location": "Zurich"},
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_search_agent_returns_409_when_exists(client, create_user_in_db, jwt_service):
    user = await create_user_in_db(email="agent_409@test.com", password="secret")
    token = jwt_service.create_access_token(
        subject=str(user.id),
        extra={"role": "user", "email": user.email},
    )

    fake_uc = AsyncMock(spec=CreateSearchAgentUseCase)
    fake_uc.execute.side_effect = ConflictError(
        code="search_agent_already_exists",
        details="Candidate already has a search agent.",
    )
    app.dependency_overrides[get_create_search_agent_use_case] = lambda: fake_uc

    response = await client.post(
        "/api/v1/search-agents",
        headers={"Authorization": f"Bearer {token}"},
        json={"keywords": "python", "location": "Zurich"},
    )

    app.dependency_overrides.pop(get_create_search_agent_use_case, None)

    assert response.status_code == 409


# ---------------------------------------------------------------------------
# GET /search-agents/me
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_search_agent_returns_200(client, create_user_in_db, jwt_service):
    user = await create_user_in_db(email="agent_get@test.com", password="secret")
    token = jwt_service.create_access_token(
        subject=str(user.id),
        extra={"role": "user", "email": user.email},
    )

    fake_agent = _make_agent(candidate_id=user.id)
    fake_uc = AsyncMock(spec=GetSearchAgentUseCase)
    fake_uc.execute.return_value = fake_agent
    app.dependency_overrides[get_get_search_agent_use_case] = lambda: fake_uc

    response = await client.get(
        "/api/v1/search-agents/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    app.dependency_overrides.pop(get_get_search_agent_use_case, None)

    assert response.status_code == 200
    data = response.json()
    assert data["keywords"] == "python developer"


@pytest.mark.asyncio
async def test_get_search_agent_returns_null_when_none(client, create_user_in_db, jwt_service):
    user = await create_user_in_db(email="agent_get_none@test.com", password="secret")
    token = jwt_service.create_access_token(
        subject=str(user.id),
        extra={"role": "user", "email": user.email},
    )

    fake_uc = AsyncMock(spec=GetSearchAgentUseCase)
    fake_uc.execute.return_value = None
    app.dependency_overrides[get_get_search_agent_use_case] = lambda: fake_uc

    response = await client.get(
        "/api/v1/search-agents/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    app.dependency_overrides.pop(get_get_search_agent_use_case, None)

    assert response.status_code == 200
    assert response.json() is None


# ---------------------------------------------------------------------------
# PUT /search-agents/{agent_id}
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_update_search_agent_returns_200(client, create_user_in_db, jwt_service):
    user = await create_user_in_db(email="agent_update@test.com", password="secret")
    token = jwt_service.create_access_token(
        subject=str(user.id),
        extra={"role": "user", "email": user.email},
    )
    agent_id = uuid4()
    fake_agent = _make_agent(id=agent_id, candidate_id=user.id, keywords="data engineer")
    fake_uc = AsyncMock(spec=UpdateSearchAgentUseCase)
    fake_uc.execute.return_value = fake_agent
    app.dependency_overrides[get_update_search_agent_use_case] = lambda: fake_uc

    response = await client.put(
        f"/api/v1/search-agents/{agent_id}",
        headers={"Authorization": f"Bearer {token}"},
        json={"keywords": "data engineer"},
    )

    app.dependency_overrides.pop(get_update_search_agent_use_case, None)

    assert response.status_code == 200
    assert response.json()["keywords"] == "data engineer"


@pytest.mark.asyncio
async def test_update_search_agent_returns_404_when_not_found(client, create_user_in_db, jwt_service):
    user = await create_user_in_db(email="agent_update_404@test.com", password="secret")
    token = jwt_service.create_access_token(
        subject=str(user.id),
        extra={"role": "user", "email": user.email},
    )
    agent_id = uuid4()
    fake_uc = AsyncMock(spec=UpdateSearchAgentUseCase)
    fake_uc.execute.side_effect = NotFoundError(
        code="search_agent_not_found",
        details=f"SearchAgent {agent_id} not found.",
    )
    app.dependency_overrides[get_update_search_agent_use_case] = lambda: fake_uc

    response = await client.put(
        f"/api/v1/search-agents/{agent_id}",
        headers={"Authorization": f"Bearer {token}"},
        json={"keywords": "python"},
    )

    app.dependency_overrides.pop(get_update_search_agent_use_case, None)

    assert response.status_code == 404


# ---------------------------------------------------------------------------
# DELETE /search-agents/{agent_id}
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_delete_search_agent_returns_204(client, create_user_in_db, jwt_service):
    user = await create_user_in_db(email="agent_delete@test.com", password="secret")
    token = jwt_service.create_access_token(
        subject=str(user.id),
        extra={"role": "user", "email": user.email},
    )
    agent_id = uuid4()
    fake_uc = AsyncMock(spec=DeleteSearchAgentUseCase)
    fake_uc.execute.return_value = None
    app.dependency_overrides[get_delete_search_agent_use_case] = lambda: fake_uc

    response = await client.delete(
        f"/api/v1/search-agents/{agent_id}",
        headers={"Authorization": f"Bearer {token}"},
    )

    app.dependency_overrides.pop(get_delete_search_agent_use_case, None)

    assert response.status_code == 204


@pytest.mark.asyncio
async def test_delete_search_agent_returns_404_when_not_found(client, create_user_in_db, jwt_service):
    user = await create_user_in_db(email="agent_delete_404@test.com", password="secret")
    token = jwt_service.create_access_token(
        subject=str(user.id),
        extra={"role": "user", "email": user.email},
    )
    agent_id = uuid4()
    fake_uc = AsyncMock(spec=DeleteSearchAgentUseCase)
    fake_uc.execute.side_effect = NotFoundError(
        code="search_agent_not_found",
        details=f"SearchAgent {agent_id} not found.",
    )
    app.dependency_overrides[get_delete_search_agent_use_case] = lambda: fake_uc

    response = await client.delete(
        f"/api/v1/search-agents/{agent_id}",
        headers={"Authorization": f"Bearer {token}"},
    )

    app.dependency_overrides.pop(get_delete_search_agent_use_case, None)

    assert response.status_code == 404


# ---------------------------------------------------------------------------
# POST /search-agents/{agent_id}/run
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_run_search_agent_returns_200(client, create_user_in_db, jwt_service):
    from datetime import datetime, timezone
    from app.application.job_search.search_agent_use_cases import RunSearchAgentResult
    user = await create_user_in_db(email="agent_run@test.com", password="secret")
    token = jwt_service.create_access_token(
        subject=str(user.id),
        extra={"role": "user", "email": user.email},
    )
    agent_id = uuid4()
    fake_agent = _make_agent(id=agent_id, candidate_id=user.id)
    fake_agent.last_run_at = datetime.now(timezone.utc)
    fake_uc = AsyncMock(spec=RunSearchAgentUseCase)
    fake_uc.execute.return_value = RunSearchAgentResult(agent=fake_agent, jobs_found=5)
    app.dependency_overrides[get_run_search_agent_use_case] = lambda: fake_uc

    response = await client.post(
        f"/api/v1/search-agents/{agent_id}/run",
        headers={"Authorization": f"Bearer {token}"},
    )

    app.dependency_overrides.pop(get_run_search_agent_use_case, None)

    assert response.status_code == 200
    data = response.json()
    assert data["agent"]["last_run_at"] is not None
    assert data["jobs_found"] == 5


@pytest.mark.asyncio
async def test_run_search_agent_returns_404_when_not_found(client, create_user_in_db, jwt_service):
    user = await create_user_in_db(email="agent_run_404@test.com", password="secret")
    token = jwt_service.create_access_token(
        subject=str(user.id),
        extra={"role": "user", "email": user.email},
    )
    agent_id = uuid4()
    fake_uc = AsyncMock(spec=RunSearchAgentUseCase)
    fake_uc.execute.side_effect = NotFoundError(
        code="search_agent_not_found",
        details=f"SearchAgent {agent_id} not found.",
    )
    app.dependency_overrides[get_run_search_agent_use_case] = lambda: fake_uc

    response = await client.post(
        f"/api/v1/search-agents/{agent_id}/run",
        headers={"Authorization": f"Bearer {token}"},
    )

    app.dependency_overrides.pop(get_run_search_agent_use_case, None)

    assert response.status_code == 404
