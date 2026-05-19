from fastapi import FastAPI
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded
from starlette.middleware.cors import CORSMiddleware
from starlette.requests import Request

from app.core.config import settings
from app.core.handlers import setup_routers
from app.core.logging import setup_logging
from app.core.rate_limiting import limiter
from app.presentation.api.exception_handlers import setup_exception_handlers
from app.presentation.middlewares.request_context import RequestContextMiddleware


async def _rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    return JSONResponse(
        status_code=429,
        content={"code": "rate_limit_exceeded", "detail": str(exc.detail)},
    )


def create_app() -> FastAPI:
    # Setup logging, config, database connections, etc. here if needed
    setup_logging()

    app = FastAPI(
        title="JobAI API Platform",
        version="1.0.0",
    )

    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    app.add_middleware(RequestContextMiddleware)

    setup_routers(app, prefix="/api/v1")
    setup_exception_handlers(app) # This need to be called on the handler.py

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ALLOW_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health", tags=["health"])
    def health() -> dict:
        return {"status": "ok"}


    return app

app = create_app()
