from fastapi import FastAPI

from app.presentation.api.v1.users_routes import router as users_router
from app.presentation.api.v1.auth_routes import router as auth_router

def setup_routers(app: FastAPI, prefix: str = "/api/v1") -> None:
    """
    Sets up FastAPI routers for FastAPI
    This is a "facade" layer of presentation
    :param app:
    :param prefix:
    :return:
    """
    routers = [
        users_router,
        # auth_router,
    ]

    for router in routers:
        app.include_router(router, prefix=prefix)
