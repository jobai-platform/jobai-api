from fastapi import FastAPI

from app.presentation.api.v1.ai_analysis_routes import router as ai_analysis_router
from app.presentation.api.v1.auth_routes import router as auth_router
from app.presentation.api.v1.candidate_profile_routes import router as candidate_profile_router
from app.presentation.api.v1.job_search_routes import router as job_search_router
from app.presentation.api.v1.search_agent_routes import router as search_agent_router
from app.presentation.api.v1.stripe_routes import router as stripe_router
from app.presentation.api.v1.users_routes import router as users_router


def setup_routers(app: FastAPI, prefix: str = "/api/v1") -> None:
    """
    Sets up FastAPI routers for FastAPI
    This is a "facade" layer of presentation
    :param app: FastAPI application
    :param prefix: prefix for all routes
    :return: None
    """
    routers = [
        users_router,
        auth_router,
        stripe_router,
        job_search_router,
        search_agent_router,
        candidate_profile_router,
        ai_analysis_router,
    ]

    for router in routers:
        app.include_router(router, prefix=prefix)
