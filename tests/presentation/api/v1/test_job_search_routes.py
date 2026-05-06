import pytest
from unittest.mock import AsyncMock

from app.application.job_search.dto import JobSearchResult
from app.application.job_search.use_cases import SearchJobsUseCase
from app.core.dependency import get_search_jobs_use_case
from tests.fakes.job_search.fake_job_scraper_gateway import make_scraped_job

import uuid


def make_fake_search_result(**kwargs) -> JobSearchResult:
    jobs = kwargs.get("jobs", [make_scraped_job()])
    return JobSearchResult(
        jobs=jobs,
        total=len(jobs),
        keywords=kwargs.get("keywords", "Python"),
        location=kwargs.get("location", "Geneva"),
        source=kwargs.get("source", "linkedin"),
    )


@pytest.mark.asyncio
async def test_search_jobs_returns_200(client, create_user_in_db, jwt_service):
    user = await create_user_in_db(email="searcher@test.com", password="secret")
    token = jwt_service.create_access_token(
        subject=str(user.id),
        extra={"role": "user", "email": user.email},
    )

    fake_result = make_fake_search_result(
        jobs=[
            make_scraped_job(job_id="001", title="Python Dev"),
            make_scraped_job(job_id="002", title="Backend Engineer"),
        ],
        keywords="Python",
        location="Geneva",
    )

    fake_use_case = AsyncMock(spec=SearchJobsUseCase)
    fake_use_case.execute.return_value = fake_result

    from app.main import app
    app.dependency_overrides[get_search_jobs_use_case] = lambda: fake_use_case

    response = await client.post(
        "/api/v1/jobs/search",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "keywords": "Python",
            "location": "Geneva",
            "limit": 25,
        },
    )

    app.dependency_overrides.pop(get_search_jobs_use_case, None)

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 2
    assert data["has_results"] is True
    assert data["keywords"] == "Python"
    assert data["location"] == "Geneva"
    assert data["source"] == "linkedin"
    assert len(data["jobs"]) == 2
    assert data["jobs"][0]["title"] == "Python Dev"
    assert data["jobs"][0]["source"] == "linkedin"


@pytest.mark.asyncio
async def test_search_jobs_returns_401_without_token(client):
    response = await client.post(
        "/api/v1/jobs/search",
        json={"keywords": "Python", "location": "Geneva"},
    )
    assert response.status_code == 401
    assert response.json()["code"] == "invalid_authentication"


@pytest.mark.asyncio
async def test_search_jobs_returns_422_on_invalid_payload(
    client, create_user_in_db, jwt_service
):
    user = await create_user_in_db(email="searcher2@test.com", password="secret")
    token = jwt_service.create_access_token(
        subject=str(user.id),
        extra={"role": "user", "email": user.email},
    )

    response = await client.post(
        "/api/v1/jobs/search",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "keywords": "",       # min_length=1 → validation error
            "location": "Geneva",
        },
    )

    assert response.status_code == 422
    assert response.json()["code"] == "validation_error"


@pytest.mark.asyncio
async def test_search_jobs_returns_empty_result(
    client, create_user_in_db, jwt_service
):
    user = await create_user_in_db(email="searcher3@test.com", password="secret")
    token = jwt_service.create_access_token(
        subject=str(user.id),
        extra={"role": "user", "email": user.email},
    )

    fake_result = make_fake_search_result(jobs=[], keywords="Cobol", location="Moon")
    fake_use_case = AsyncMock(spec=SearchJobsUseCase)
    fake_use_case.execute.return_value = fake_result

    from app.main import app
    app.dependency_overrides[get_search_jobs_use_case] = lambda: fake_use_case

    response = await client.post(
        "/api/v1/jobs/search",
        headers={"Authorization": f"Bearer {token}"},
        json={"keywords": "Cobol", "location": "Moon"},
    )

    app.dependency_overrides.pop(get_search_jobs_use_case, None)

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 0
    assert data["has_results"] is False
    assert data["jobs"] == []


@pytest.mark.asyncio
async def test_search_jobs_returns_502_when_scraper_unavailable(
    client, create_user_in_db, jwt_service
):
    user = await create_user_in_db(email="searcher4@test.com", password="secret")
    token = jwt_service.create_access_token(
        subject=str(user.id),
        extra={"role": "user", "email": user.email},
    )

    fake_use_case = AsyncMock(spec=SearchJobsUseCase)
    fake_use_case.execute.side_effect = RuntimeError("Chromium crashed")

    from app.main import app
    app.dependency_overrides[get_search_jobs_use_case] = lambda: fake_use_case

    response = await client.post(
        "/api/v1/jobs/search",
        headers={"Authorization": f"Bearer {token}"},
        json={"keywords": "Python", "location": "Geneva"},
    )

    app.dependency_overrides.pop(get_search_jobs_use_case, None)

    assert response.status_code == 502
