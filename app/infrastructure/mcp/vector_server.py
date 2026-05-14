from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from typing import Any
from uuid import UUID

from app.application.ai_analysis.ports import VectorStorePort
from app.core.config import settings
from app.domain.ai_analysis.ports import EmbeddingPort
from app.infrastructure.ai.ollama_embedding_adapter import OllamaEmbeddingAdapter
from app.infrastructure.ai.timescale_vector_store import TimescaleVectorStoreAdapter
from app.infrastructure.config.database import get_async_session
from app.infrastructure.mcp.auth import MCPAuth
from app.infrastructure.mcp.serialization import serialize_similarity_result
from app.infrastructure.mcp.server import MCPTool, StdioMCPServer


def _parse_top_k(value: Any) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("top_k must be an integer")
    top_k = value
    if not 1 <= top_k <= 100:
        raise ValueError("top_k must be between 1 and 100")
    return top_k


def build_vector_server(
    *,
    embedding_port: EmbeddingPort,
    vector_store: VectorStorePort,
    auth: MCPAuth,
    commit: Callable[[], Awaitable[None]] | None = None,
) -> StdioMCPServer:
    server = StdioMCPServer(name="jobai-vector-mcp")

    async def embed_text(arguments: dict[str, Any]) -> dict[str, Any]:
        auth.require_internal_token(arguments)
        vector = await embedding_port.generate_embedding(arguments["text"])
        return {"vector": vector, "dimensions": len(vector)}

    async def similarity_search(arguments: dict[str, Any]) -> dict[str, Any]:
        auth.require_internal_token(arguments)
        target = arguments.get("target", "jobs")
        vector = arguments["vector"]
        top_k = _parse_top_k(arguments.get("top_k", 20))
        filters = arguments.get("filters")

        if target == "jobs":
            results = await vector_store.search_similar_jobs(
                query_vector=vector,
                top_k=top_k,
                filters=filters,
            )
        elif target == "candidates":
            results = await vector_store.search_similar_candidates(
                query_vector=vector,
                top_k=top_k,
                filters=filters,
            )
        else:
            raise ValueError("target must be 'jobs' or 'candidates'")

        return {"results": [serialize_similarity_result(result) for result in results]}

    async def upsert(arguments: dict[str, Any]) -> dict[str, Any]:
        auth.require_internal_token(arguments)
        target = arguments["target"]
        vector = arguments["vector"]
        metadata = arguments.get("metadata", {})

        if target == "candidate":
            candidate_id = UUID(arguments["candidate_id"])
            await vector_store.upsert_candidate(
                candidate_id=candidate_id,
                vector=vector,
                metadata=metadata,
            )
            if commit is not None:
                await commit()
            return {"target": target, "id": str(candidate_id), "status": "upserted"}
        if target == "job":
            job_posting_id = UUID(arguments["job_posting_id"])
            await vector_store.upsert_job(
                job_posting_id=job_posting_id,
                vector=vector,
                metadata=metadata,
            )
            if commit is not None:
                await commit()
            return {"target": target, "id": str(job_posting_id), "status": "upserted"}

        raise ValueError("target must be 'candidate' or 'job'")

    server.add_tool(
        MCPTool(
            name="embed_text",
            description="Generate an embedding vector for text.",
            input_schema={
                "type": "object",
                "properties": {
                    "token": {"type": "string"},
                    "text": {"type": "string"},
                },
                "required": ["token", "text"],
            },
            handler=embed_text,
        )
    )
    server.add_tool(
        MCPTool(
            name="similarity_search",
            description="Search similar JobPostings or Candidates from a query vector.",
            input_schema={
                "type": "object",
                "properties": {
                    "token": {"type": "string"},
                    "vector": {"type": "array", "items": {"type": "number"}},
                    "target": {"type": "string", "enum": ["jobs", "candidates"]},
                    "top_k": {"type": "integer", "minimum": 1, "maximum": 100},
                    "filters": {"type": "object"},
                },
                "required": ["token", "vector"],
            },
            handler=similarity_search,
        )
    )
    server.add_tool(
        MCPTool(
            name="upsert",
            description="Upsert a Candidate or JobPosting embedding.",
            input_schema={
                "type": "object",
                "properties": {
                    "token": {"type": "string"},
                    "target": {"type": "string", "enum": ["candidate", "job"]},
                    "candidate_id": {"type": "string", "format": "uuid"},
                    "job_posting_id": {"type": "string", "format": "uuid"},
                    "vector": {"type": "array", "items": {"type": "number"}},
                    "metadata": {"type": "object"},
                },
                "required": ["token", "target", "vector"],
            },
            handler=upsert,
        )
    )
    return server


async def main() -> None:
    async for session in get_async_session():
        server = build_vector_server(
            embedding_port=OllamaEmbeddingAdapter(
                base_url=settings.OLLAMA_BASE_URL,
                model=settings.OLLAMA_EMBEDDING_MODEL,
            ),
            vector_store=TimescaleVectorStoreAdapter(session=session),
            auth=MCPAuth(),
            commit=session.commit,
        )
        await server.run()


if __name__ == "__main__":
    asyncio.run(main())
