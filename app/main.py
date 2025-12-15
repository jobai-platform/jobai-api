from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware

from app.core.handlers import setup_routers
from app.presentation.api.exception_handlers import setup_exception_handlers


def create_app() -> FastAPI:
    app = FastAPI(
        title="JobAI API Platform",
        version="1.0.0",
    )

    setup_routers(app, prefix="/api/v1")
    setup_exception_handlers(app) # This need to be called on the handler.py

    # app.add_middleware(
    #     CORSMiddleware,
    #     allow_origins=["*"],
    #     allow_credentials=True,
    #     allow_methods=["*"],
    #     allow_headers=["*"],
    # )

    @app.get("/health", tags=["health"])
    def health() -> dict:
        return {"status": "ok"}


    return app

app = create_app()

