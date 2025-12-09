from fastapi import FastAPI

from .handlers import setup_routers

app = FastAPI(title="JobAI Backend", version="1.0.0")


setup_routers(app, prefix="/api/v1")

@app.get("/health", tags=["health"])
def health() -> dict:
    return {"status": "ok"}
