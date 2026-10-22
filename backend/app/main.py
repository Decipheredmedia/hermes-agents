"""Stage 1 Instagram agent API."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api.content import router
from backend.app.database import Base, engine
from backend.models import content as _content_models  # Register table metadata.

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Instagram Agent Platform",
    description="Stage 1 draft and approval API. Instagram actions are mock-only.",
    version="0.1.0",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8080", "http://127.0.0.1:8080"],
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)
app.include_router(router)


@app.get("/health")
def health():
    return {"status": "ok", "instagram_mode": "mock"}
