from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.domain.common.exceptions import (
    AppError,
    NotFoundError,
    ConflictError,
    UnauthorizedError,
    ForbiddenError,
    BadRequestError,
    ValidationError,
)


def _payload_error_response(exc: AppError) -> dict:
    return {
        "detail": exc.details,
        "code": exc.code,
    }


def setup_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(NotFoundError)
    async def handle_not_found(_: Request, exc: NotFoundError):
        return JSONResponse(
            status_code=404,
            content=_payload_error_response(exc)
        )

    @app.exception_handler(ConflictError)
    async def handle_conflict(_: Request, exc: ConflictError):
        return JSONResponse(
            status_code=409,
            content=_payload_error_response(exc)
        )

    @app.exception_handler(UnauthorizedError)
    async def handle_unauthorized(_: Request, exc: UnauthorizedError):
        return JSONResponse(
            status_code=401,
            content=_payload_error_response(exc)
        )

    @app.exception_handler(ForbiddenError)
    async def handle_forbidden(_: Request, exc: ForbiddenError):
        return JSONResponse(
            status_code=403,
            content=_payload_error_response(exc)
        )

    @app.exception_handler(BadRequestError)
    async def handle_bad_request(_: Request, exc: BadRequestError):
        return JSONResponse(
            status_code=400,
            content=_payload_error_response(exc)
        )

    @app.exception_handler(ValidationError)
    async def handle_validation_error(_: Request, exc: ValidationError):
        return JSONResponse(
            status_code=422,
            content=_payload_error_response(exc)
        )
