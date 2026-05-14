from __future__ import annotations

import asyncio
from typing import Any
from uuid import UUID

from app.application.users.candidate_profile_ports import CandidateProfileRepository
from app.infrastructure.config.database import get_async_session
from app.infrastructure.mcp.auth import MCPAuth
from app.infrastructure.mcp.serialization import serialize_candidate_profile, serialize_cv_text
from app.infrastructure.mcp.server import MCPTool, StdioMCPServer
from app.infrastructure.persistence.repositories.candidate_profile_sqlalchemy import (
    SQLAlchemyCandidateProfileRepository,
)

PROFILE_TOOL_SCHEMA = {
    "type": "object",
    "properties": {
        "token": {"type": "string"},
        "user_id": {"type": "string", "format": "uuid"},
    },
    "required": ["token", "user_id"],
}


def build_profile_server(
    *,
    profile_repo: CandidateProfileRepository,
    auth: MCPAuth,
) -> StdioMCPServer:
    server = StdioMCPServer(name="jobai-profile-mcp")

    async def get_profile(arguments: dict[str, Any]) -> dict[str, Any]:
        auth.require_internal_token(arguments)
        profile = await profile_repo.get_by_user_id(UUID(arguments["user_id"]))
        if profile is None:
            return {"profile": None}
        return serialize_candidate_profile(profile)

    async def get_cv_text(arguments: dict[str, Any]) -> dict[str, Any]:
        auth.require_internal_token(arguments)
        profile = await profile_repo.get_by_user_id(UUID(arguments["user_id"]))
        if profile is None:
            return {
                "user_id": arguments["user_id"],
                "cv_url": None,
                "text": None,
                "status": "profile_not_found",
            }
        return serialize_cv_text(profile)

    server.add_tool(
        MCPTool(
            name="get_profile",
            description="Return a Candidate profile by user_id.",
            input_schema=PROFILE_TOOL_SCHEMA,
            handler=get_profile,
        )
    )
    server.add_tool(
        MCPTool(
            name="get_cv_text",
            description="Return CV text metadata for a Candidate profile.",
            input_schema=PROFILE_TOOL_SCHEMA,
            handler=get_cv_text,
        )
    )
    return server


async def main() -> None:
    async for session in get_async_session():
        server = build_profile_server(
            profile_repo=SQLAlchemyCandidateProfileRepository(session=session),
            auth=MCPAuth(),
        )
        await server.run()


if __name__ == "__main__":
    asyncio.run(main())
