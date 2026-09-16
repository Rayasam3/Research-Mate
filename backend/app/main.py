"""
FastAPI entrypoint.
Phase 0: health check, CORS, rate-limit middleware wired in from day one.
Phase 1: /api/search added.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.api.agent import router as agent_router
from app.api.ingest import router as ingest_router
from app.api.search import router as search_router
from app.api.summarize import router as summarize_router
from app.core.config import settings
from app.core.limiter import limiter

app = FastAPI(title="Research Mate API", version="0.1.0")

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(search_router, prefix="/api", tags=["search"])
app.include_router(ingest_router, prefix="/api", tags=["ingest"])
app.include_router(agent_router, prefix="/api", tags=["agent"])


@app.get("/health")
def health_check():
    """Confirms the app is up and which environment it's configured for."""
    return {"status": "ok", "env": settings.app_env}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host=settings.app_host, port=settings.app_port, reload=True)
