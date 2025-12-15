import logging
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette import status
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.config import settings
from app.domain.common.exceptions import (
    AppError,
    NotFoundError,
    ConflictError,
    UnauthorizedError,
    ForbiddenError,
    BadRequestError,
    ValidationError,
)


logger = logging.getLogger("app.exceptions")


def _payload_error_response(*, code: str, detail: str, **extra: Any) -> dict[str, Any]:
    """Constructs a standardized error response payload."""
    payload: dict[str, Any] = {
        "code": code,
        "detail": detail,
    }
    payload.update(extra)
    return payload


def _payload_from_app_error(exc: AppError) -> dict[str, Any]:
    return _payload_error_response(code=exc.code, detail=exc.detail)


def _code_from_status(status_code: int) -> str:
    # Central mapping for native HTTP status codes to application error codes
    return {
        400: "bad_request",
        401: "insufficient_authentication",
        403: "insufficient_permissions",
        404: "resource_not_found",
        409: "conflict_error",
        422: "validation_error",
    }.get(status_code, "http_error")


def setup_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(BadRequestError)
    async def handle_bad_request(_: Request, exc: BadRequestError):
        return JSONResponse(
            status_code=400,
            content=_payload_from_app_error(exc)
        )

    @app.exception_handler(UnauthorizedError)
    async def handle_unauthorized(_: Request, exc: UnauthorizedError):
        return JSONResponse(
            status_code=401,
            content=_payload_from_app_error(exc)
        )

    @app.exception_handler(ForbiddenError)
    async def handle_forbidden(_: Request, exc: ForbiddenError):
        return JSONResponse(
            status_code=403,
            content=_payload_from_app_error(exc)
        )

    @app.exception_handler(NotFoundError)
    async def handle_not_found(_: Request, exc: NotFoundError):
        return JSONResponse(
            status_code=404,
            content=_payload_from_app_error(exc)
        )

    @app.exception_handler(ConflictError)
    async def handle_conflict(_: Request, exc: ConflictError):
        return JSONResponse(
            status_code=409,
            content=_payload_from_app_error(exc)
        )

    @app.exception_handler(ValidationError)
    async def handle_validation_error(_: Request, exc: ValidationError):
        return JSONResponse(
            status_code=422,
            content=_payload_from_app_error(exc)
        )


    # --- FastAPI / Pydantic exception handlers ---

    @app.exception_handler(RequestValidationError)
    async def handle_request_validation_error(_: Request, exc: RequestValidationError):
        # Pydantic-style validation error
        return JSONResponse(
            status_code=422,
            content=_payload_error_response(
                code="validation_error",
                detail="Request validation failed",
                errors=exc.errors(),
            )
        )


    # --- Starlette HTTPException ( including OAuth2 errors if auto_error=True, etc. ) ---

    @app.exception_handler(StarletteHTTPException)
    async def handle_http_exception(_: Request, exc: StarletteHTTPException):
        # Normalize FastAPI / Starlette HTTP exceptions
        detail = exc.detail if isinstance(exc.detail, str) else "HTTP error occurred"
        code = _code_from_status(exc.status_code)

        return JSONResponse(
            status_code=exc.status_code,
            content=_payload_error_response(
                code=code,
                detail=detail
            )
        )


    # --- Catch-all 500 handler exception ---

    @app.exception_handler(Exception)
    async def handle_generic_exception(request: Request, exc: Exception):
        logger.error(f"Unhandled exception on $s $s", request.method, request.url)

        payload = _payload_error_response(
            code="internal_server_error",
            detail="An internal server error occurred"
        )

        # Optionally include exception details in non-production environments
        if settings.DEBUG:
            payload["debug"] = {
                "type": exc.__class__.__name__,
                "message": str(exc)
            }

        return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content=payload)

