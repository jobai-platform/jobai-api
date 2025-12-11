from fastapi import FastAPI


def setup_routers(app: FastAPI, prefix: str | None = None) -> None:
    from old.app.api.v1.usersRoutes import router as users_router

    routers = [
        users_router,
    ]

    for router in routers:
        app.include_router(router, prefix=prefix or "")
