from fastapi import FastAPI

app = FastAPI(title="JobAI Backend", version="1.0.0")


@app.get("/health", tags=["health"])
def health() -> dict:
    return {"status": "ok"}
