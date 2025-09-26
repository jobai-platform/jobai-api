from fastapi import FastAPI, status


def setup_routers(app: FastAPI, prefix: str | None = None) -> None:
    from app.api.v1.usersRoutes import router as users_router


    routers = [
        users_router,
    ]

    for router in routers:
        app.include_router(router, prefix=prefix or "")
