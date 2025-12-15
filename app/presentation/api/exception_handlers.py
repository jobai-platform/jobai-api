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
    return _payload_error_response(code=exc.code, detail=exc.details)


def _code_from_status(status_code: int) -> str:
    """
    Central mapping for native HTTP status codes to application error codes.
    Keep these aligned with domain/presentation codes used elsewhere.
    :param status_code: HTTP status code
    :return: Application error code string
    """
    return {
        400: "bad_request",
        401: "invalid_authentication",
        403: "insufficient_permissions",
        404: "resource_not_found",
        409: "conflict_error",
        422: "validation_error",
    }.get(status_code, "http_error")


def _log_context(request: Request) -> dict[str, Any]:
    return {
        "request_id": getattr(request.state, "request_id", None),
        "method": request.method,
        "url": str(request.url),
        "user_id": getattr(request.state, "user_id", None),
        "user_email": getattr(request.state, "user_email", None),
        "user_role": getattr(request.state, "user_role", None),
    }


def setup_exception_handlers(app: FastAPI) -> None:
    # -------------------------
    # Domain/Application errors
    # -------------------------
    @app.exception_handler(BadRequestError)
    async def handle_bad_request(request: Request, exc: BadRequestError):
        logger.info(f"BadRequestError", extra=_log_context(request))
        return JSONResponse(
            status_code=400,
            content=_payload_from_app_error(exc)
        )

    @app.exception_handler(UnauthorizedError)
    async def handle_unauthorized(request: Request, exc: UnauthorizedError):
        logger.info("UnauthorizedError", extra=_log_context(request))
        return JSONResponse(
            status_code=401,
            content=_payload_from_app_error(exc)
        )

    @app.exception_handler(ForbiddenError)
    async def handle_forbidden(request: Request, exc: ForbiddenError):
        logger.info("ForbiddenError", extra=_log_context(request))
        return JSONResponse(
            status_code=403,
            content=_payload_from_app_error(exc)
        )

    @app.exception_handler(NotFoundError)
    async def handle_not_found(request: Request, exc: NotFoundError):
        logger.info("NotFoundError", extra=_log_context(request))
        return JSONResponse(
            status_code=404,
            content=_payload_from_app_error(exc)
        )

    @app.exception_handler(ConflictError)
    async def handle_conflict(request: Request, exc: ConflictError):
        logger.info("ConflictError", extra=_log_context(request))
        return JSONResponse(
            status_code=409,
            content=_payload_from_app_error(exc)
        )

    @app.exception_handler(ValidationError)
    async def handle_validation_error(request: Request, exc: ValidationError):
        logger.info("ValidationError", extra=_log_context(request))
        return JSONResponse(
            status_code=422,
            content=_payload_from_app_error(exc)
        )

    # -------------------------
    # FastAPI/Pydantic validation
    # -------------------------
    @app.exception_handler(RequestValidationError)
    async def handle_request_validation_error(request: Request, exc: RequestValidationError):
        logger.info("RequestValidationError", extra=_log_context(request))
        # Pydantic-style validation error
        return JSONResponse(
            status_code=422,
            content=_payload_error_response(
                code="validation_error",
                detail="Validation error",
                # errors=exc.errors()
                errors=[
                    {"loc": ["body", "email"], "msg": "...", "type": "..."}
                ],
            )
        )

    # -------------------------
    # Starlette/FastAPI HTTPException
    # (e.g. 404 Not Found route, 405, etc.)
    # -------------------------
    @app.exception_handler(StarletteHTTPException)
    async def handle_http_exception(request: Request, exc: StarletteHTTPException):
        # Normalize FastAPI / Starlette HTTP exceptions
        logger.info("HTTPException", extra={**_log_context(request), "status_code": exc.status_code})
        detail = exc.detail if isinstance(exc.detail, str) else "HTTP error occurred"

        return JSONResponse(
            status_code=exc.status_code,
            content=_payload_error_response(
                code=_code_from_status(exc.status_code),
                detail=detail
            ),
            headers=getattr(exc, "headers", None)
        )

    # -------------------------
    # Catch-all 500
    # -------------------------
    @app.exception_handler(Exception)
    async def handle_unexpected_exception(request: Request, exc: Exception):
        logger.error("Unhandled exception", extra=_log_context(request))

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

        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=payload
        )

