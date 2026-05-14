from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from jose import JWTError

from app.infrastructure.security.jwt_service import JWTService


class MCPAuthError(Exception):
    """Raised when an MCP tool call is not authorized."""


class MCPAuth:
    def __init__(self, jwt_service: JWTService | None = None) -> None:
        self._jwt_service = jwt_service or JWTService()

    def require_internal_token(self, arguments: Mapping[str, Any]) -> Mapping[str, Any]:
        token = arguments.get("token")
        if not isinstance(token, str) or not token:
            raise MCPAuthError("Missing internal JWT token")

        try:
            claims = self._jwt_service.decode_token(token)
        except JWTError as exc:
            raise MCPAuthError("Invalid internal JWT token") from exc

        scope = claims.get("scope", "")
        scopes = scope.split() if isinstance(scope, str) else []
        if "mcp:internal" not in scopes:
            raise MCPAuthError("Internal JWT token lacks mcp:internal scope")

        return claims
