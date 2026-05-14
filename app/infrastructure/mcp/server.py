from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from enum import Enum
import json
import sys
from typing import Any

from app.infrastructure.mcp.auth import MCPAuthError

ToolHandler = Callable[[dict[str, Any]], Awaitable[dict[str, Any]]]


class MCPError(Enum):
    INVALID_REQUEST = -32600
    METHOD_NOT_FOUND = -32601
    INVALID_PARAMS = -32602
    INTERNAL_ERROR = -32603
    UNAUTHORIZED = -32001
    NOT_FOUND = -32004
    UNKNOWN_TOOL = -32010

    @property
    def code(self) -> int:
        return self.value


@dataclass(frozen=True, slots=True)
class MCPTool:
    name: str
    description: str
    input_schema: dict[str, Any]
    handler: ToolHandler

    def descriptor(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "inputSchema": self.input_schema,
        }


class StdioMCPServer:
    def __init__(self, *, name: str, version: str = "0.1.0") -> None:
        self._name = name
        self._version = version
        self._tools: dict[str, MCPTool] = {}

    def add_tool(self, tool: MCPTool) -> None:
        self._tools[tool.name] = tool

    async def handle(self, request: dict[str, Any]) -> dict[str, Any]:
        request_id = request.get("id")
        method = request.get("method")

        try:
            if method == "initialize":
                result = {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {"tools": {}},
                    "serverInfo": {"name": self._name, "version": self._version},
                }
            elif method == "ping":
                result = {}
            elif method == "tools/list":
                result = {"tools": [tool.descriptor() for tool in self._tools.values()]}
            elif method == "tools/call":
                result = await self._call_tool(request.get("params", {}))
            else:
                return _error_response(
                    request_id,
                    MCPError.METHOD_NOT_FOUND,
                    f"Unknown method: {method}",
                )
        except MCPAuthError as exc:
            return _error_response(request_id, MCPError.UNAUTHORIZED, str(exc))
        except KeyError as exc:
            return _error_response(
                request_id,
                MCPError.INVALID_PARAMS,
                f"Missing parameter: {exc.args[0]}",
            )
        except ValueError as exc:
            return _error_response(request_id, MCPError.INVALID_PARAMS, str(exc))

        return {"jsonrpc": "2.0", "id": request_id, "result": result}

    async def _call_tool(self, params: dict[str, Any]) -> dict[str, Any]:
        name = params.get("name")
        arguments = params.get("arguments", {})
        if not isinstance(name, str):
            raise ValueError("Tool name must be a string")
        if not isinstance(arguments, dict):
            raise ValueError("Tool arguments must be an object")

        tool = self._tools.get(name)
        if tool is None:
            raise UnknownToolError(f"Unknown tool: {name}")

        structured_content = await tool.handler(arguments)
        return {
            "content": [{"type": "text", "text": json.dumps(structured_content, default=str)}],
            "structuredContent": structured_content,
        }

    async def run(self) -> None:
        loop = asyncio.get_running_loop()
        while line := await loop.run_in_executor(None, sys.stdin.readline):
            response = await self.handle(json.loads(line))
            sys.stdout.write(json.dumps(response, default=str) + "\n")
            sys.stdout.flush()


class UnknownToolError(ValueError):
    pass


def _error_response(request_id: Any, error: MCPError, message: str) -> dict[str, Any]:
    code = (
        MCPError.UNKNOWN_TOOL.code
        if isinstance(error, MCPError) and message.startswith("Unknown tool:")
        else error.code
    )
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "error": {"code": code, "message": message},
    }
