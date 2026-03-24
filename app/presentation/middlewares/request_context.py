import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response


def _generate_request_id() -> str:
    return str(uuid.uuid4())


class RequestContextMiddleware(BaseHTTPMiddleware):
    """
    Middleware to add a request context to each incoming request.
    This can be used to store request-specific data that can be accessed
    throughout the request lifecycle.
    - Adds `request_id` attribute to the request object.
    - Adds `timing_metadata` attribute to the request object.
    """
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        request.state.request_id = _generate_request_id()
        start = time.perf_counter()

        response = await call_next(request)

        duration_ms = (time.perf_counter() - start) * 1000.0
        response.headers["X-Request-Id"] = request.state.request_id
        response.headers["X-Response-Time-ms"] = f"{duration_ms:.2f}"
        return response
