from __future__ import annotations

from uuid import uuid4

import pytest

from app.domain.job_search.entities import JobPosting
from app.domain.users.candidate_profile import CandidateProfile, RemotePreference
from app.infrastructure.mcp.auth import MCPAuth
from app.infrastructure.mcp.jobs_server import build_jobs_server
from app.infrastructure.mcp.profile_server import build_profile_server
from app.infrastructure.mcp.server import MCPError
from app.infrastructure.mcp.vector_server import build_vector_server
from app.infrastructure.security.jwt_service import JWTService
from tests.fakes.ai_analysis.fake_embedding_port import FakeEmbeddingPort
from tests.fakes.ai_analysis.fake_vector_store import FakeVectorStore


class FakeCandidateProfileRepository:
    def __init__(self, profile: CandidateProfile | None = None) -> None:
        self.profile = profile

    async def get_by_user_id(self, user_id):
        if self.profile and self.profile.user_id == user_id:
            return self.profile
        return None


class FakeJobPostingRepository:
    def __init__(self, jobs: list[JobPosting]) -> None:
        self.jobs = jobs

    async def get_by_id(self, job_posting_id):
        for job in self.jobs:
            if job.id == job_posting_id:
                return job
        return None

    async def search(self, *, query: str | None, location: str | None, limit: int):
        return [
            job
            for job in self.jobs
            if (query is None or query.lower() in job.title.lower())
            and (location is None or location.lower() in job.location.lower())
        ][:limit]


class RecordingCommit:
    def __init__(self) -> None:
        self.calls = 0

    async def __call__(self) -> None:
        self.calls += 1


@pytest.fixture()
def token() -> str:
    return JWTService().create_access_token("mcp-internal", {"scope": "mcp:internal"})


@pytest.mark.asyncio()
async def test_profile_server_lists_expected_tools() -> None:
    server = build_profile_server(
        profile_repo=FakeCandidateProfileRepository(),
        auth=MCPAuth(jwt_service=JWTService()),
    )

    response = await server.handle({"jsonrpc": "2.0", "id": 1, "method": "tools/list"})

    assert response["result"]["tools"] == [
        {
            "name": "get_profile",
            "description": "Return a Candidate profile by user_id.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "token": {"type": "string"},
                    "user_id": {"type": "string", "format": "uuid"},
                },
                "required": ["token", "user_id"],
            },
        },
        {
            "name": "get_cv_text",
            "description": "Return CV text metadata for a Candidate profile.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "token": {"type": "string"},
                    "user_id": {"type": "string", "format": "uuid"},
                },
                "required": ["token", "user_id"],
            },
        },
    ]


@pytest.mark.asyncio()
async def test_profile_server_get_profile_requires_internal_jwt() -> None:
    user_id = uuid4()
    profile = CandidateProfile(user_id=user_id, current_title="Python Engineer", skills=["Python"])
    server = build_profile_server(
        profile_repo=FakeCandidateProfileRepository(profile),
        auth=MCPAuth(jwt_service=JWTService()),
    )

    response = await server.handle(
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {"name": "get_profile", "arguments": {"user_id": str(user_id)}},
        }
    )

    assert response["error"]["code"] == -32001
    assert response["error"]["message"] == "Missing internal JWT token"


@pytest.mark.asyncio()
async def test_profile_server_get_profile_returns_serialized_candidate_profile(token: str) -> None:
    user_id = uuid4()
    profile = CandidateProfile(
        user_id=user_id,
        current_title="Python Engineer",
        years_of_experience=5,
        skills=["Python", "FastAPI"],
        preferred_locations=["Zurich"],
        remote_preference=RemotePreference.HYBRID,
        bio="Builds APIs",
        cv_url="s3://bucket/cv.pdf",
    )
    server = build_profile_server(
        profile_repo=FakeCandidateProfileRepository(profile),
        auth=MCPAuth(jwt_service=JWTService()),
    )

    response = await server.handle(
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": "get_profile",
                "arguments": {"token": token, "user_id": str(user_id)},
            },
        }
    )

    payload = response["result"]["structuredContent"]
    assert payload["user_id"] == str(user_id)
    assert payload["current_title"] == "Python Engineer"
    assert payload["skills"] == ["python", "fastapi"]
    assert payload["remote_preference"] == "hybrid"


@pytest.mark.asyncio()
async def test_jobs_server_search_jobs_filters_by_query_and_location(token: str) -> None:
    job_id = uuid4()
    server = build_jobs_server(
        job_repo=FakeJobPostingRepository(
            [
                JobPosting(
                    id=job_id,
                    external_id="job-1",
                    source="linkedin",
                    title="Senior Python Engineer",
                    company="JobAI",
                    location="Zurich",
                    description="Build APIs",
                    url="https://example.test/jobs/1",
                ),
                JobPosting(
                    id=uuid4(),
                    external_id="job-2",
                    source="linkedin",
                    title="Frontend Engineer",
                    company="JobAI",
                    location="Geneva",
                    description="Build UI",
                    url="https://example.test/jobs/2",
                ),
            ]
        ),
        auth=MCPAuth(jwt_service=JWTService()),
    )

    response = await server.handle(
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": "search_jobs",
                "arguments": {"token": token, "query": "python", "location": "zurich", "limit": 5},
            },
        }
    )

    assert response["result"]["structuredContent"]["jobs"][0]["id"] == str(job_id)
    assert len(response["result"]["structuredContent"]["jobs"]) == 1


@pytest.mark.asyncio()
async def test_vector_server_embed_text_and_similarity_search(token: str) -> None:
    vector_store = FakeVectorStore()
    job_id = uuid4()
    await vector_store.upsert_job(job_id, [0.1] * 768, {"title": "Python Engineer"})
    server = build_vector_server(
        embedding_port=FakeEmbeddingPort(),
        vector_store=vector_store,
        auth=MCPAuth(jwt_service=JWTService()),
    )

    embed_response = await server.handle(
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {"name": "embed_text", "arguments": {"token": token, "text": "python"}},
        }
    )
    search_response = await server.handle(
        {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {
                "name": "similarity_search",
                "arguments": {"token": token, "vector": [0.1] * 768, "target": "jobs", "top_k": 1},
            },
        }
    )

    assert len(embed_response["result"]["structuredContent"]["vector"]) == 768
    assert search_response["result"]["structuredContent"]["results"] == [
        {"id": str(job_id), "similarity_score": 1.0, "metadata": {"title": "Python Engineer"}}
    ]


@pytest.mark.asyncio()
async def test_vector_server_rejects_similarity_search_top_k_above_contract(token: str) -> None:
    server = build_vector_server(
        embedding_port=FakeEmbeddingPort(),
        vector_store=FakeVectorStore(),
        auth=MCPAuth(jwt_service=JWTService()),
    )

    response = await server.handle(
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": "similarity_search",
                "arguments": {"token": token, "vector": [0.1] * 768, "target": "jobs", "top_k": 101},
            },
        }
    )

    assert response["error"] == {"code": MCPError.INVALID_PARAMS.code, "message": "top_k must be between 1 and 100"}


@pytest.mark.asyncio()
async def test_vector_server_commits_after_successful_upsert(token: str) -> None:
    commit = RecordingCommit()
    candidate_id = uuid4()
    vector_store = FakeVectorStore()
    server = build_vector_server(
        embedding_port=FakeEmbeddingPort(),
        vector_store=vector_store,
        auth=MCPAuth(jwt_service=JWTService()),
        commit=commit,
    )

    response = await server.handle(
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": "upsert",
                "arguments": {
                    "token": token,
                    "target": "candidate",
                    "candidate_id": str(candidate_id),
                    "vector": [0.1] * 768,
                    "metadata": {"title": "Python Engineer"},
                },
            },
        }
    )

    assert response["result"]["structuredContent"] == {
        "target": "candidate",
        "id": str(candidate_id),
        "status": "upserted",
    }
    assert commit.calls == 1
    assert await vector_store.get_candidate(candidate_id) is not None


@pytest.mark.asyncio()
async def test_server_rejects_unknown_tool(token: str) -> None:
    server = build_vector_server(
        embedding_port=FakeEmbeddingPort(),
        vector_store=FakeVectorStore(),
        auth=MCPAuth(jwt_service=JWTService()),
    )

    response = await server.handle(
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {"name": "missing_tool", "arguments": {"token": token}},
        }
    )

    assert response["error"] == {"code": MCPError.UNKNOWN_TOOL.code, "message": "Unknown tool: missing_tool"}
