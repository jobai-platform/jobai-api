from __future__ import annotations

import asyncio
from typing import Any, Protocol
from uuid import UUID

from app.domain.job_search.entities import JobPosting
from app.infrastructure.config.database import get_async_session
from app.infrastructure.mcp.auth import MCPAuth
from app.infrastructure.mcp.serialization import serialize_job_posting
from app.infrastructure.mcp.server import MCPTool, StdioMCPServer
from app.infrastructure.persistence.repositories.job_posting_sqlalchemy import (
    JobPostingSQLAlchemyRepository,
)


class JobsRepository(Protocol):
    async def get_by_id(self, job_posting_id: UUID) -> JobPosting | None: ...

    async def search(
        self,
        *,
        query: str | None,
        location: str | None,
        limit: int,
    ) -> list[JobPosting]: ...


def build_jobs_server(*, job_repo: JobsRepository, auth: MCPAuth) -> StdioMCPServer:
    server = StdioMCPServer(name="jobai-jobs-mcp")

    async def get_job_posting(arguments: dict[str, Any]) -> dict[str, Any]:
        auth.require_internal_token(arguments)
        job = await job_repo.get_by_id(UUID(arguments["job_posting_id"]))
        return {"job_posting": serialize_job_posting(job) if job else None}

    async def search_jobs(arguments: dict[str, Any]) -> dict[str, Any]:
        auth.require_internal_token(arguments)
        limit = int(arguments.get("limit", 20))
        jobs = await job_repo.search(
            query=arguments.get("query"),
            location=arguments.get("location"),
            limit=limit,
        )
        return {"jobs": [serialize_job_posting(job) for job in jobs]}

    server.add_tool(
        MCPTool(
            name="get_job_posting",
            description="Return a JobPosting by id.",
            input_schema={
                "type": "object",
                "properties": {
                    "token": {"type": "string"},
                    "job_posting_id": {"type": "string", "format": "uuid"},
                },
                "required": ["token", "job_posting_id"],
            },
            handler=get_job_posting,
        )
    )
    server.add_tool(
        MCPTool(
            name="search_jobs",
            description="Search JobPostings by query and location.",
            input_schema={
                "type": "object",
                "properties": {
                    "token": {"type": "string"},
                    "query": {"type": "string"},
                    "location": {"type": "string"},
                    "limit": {"type": "integer", "minimum": 1, "maximum": 100},
                },
                "required": ["token"],
            },
            handler=search_jobs,
        )
    )
    return server


async def main() -> None:
    async for session in get_async_session():
        server = build_jobs_server(
            job_repo=JobPostingSQLAlchemyRepository(session=session),
            auth=MCPAuth(),
        )
        await server.run()


if __name__ == "__main__":
    asyncio.run(main())
