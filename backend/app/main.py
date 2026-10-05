"""
FastAPI entrypoint.
Phase 2: /api/ingest added.
Phase 3: /api/summarize added.
Phase 4: /api/agent/run and /api/agent/status added.
Phase 5: /api/compare and /api/graph/related added.

Note on Windows SSL errors: some Windows machines (often due to antivirus
or network "HTTPS scanning") can't verify certificates for outbound
requests to ArXiv/Semantic Scholar/PubMed. If you hit
SSLCertVerificationError, install `pip-system-certs` (already listed in
requirements.txt for Windows only) - it makes Python trust the same
certificates Windows itself trusts, and needs no code changes here.
"""
import logging
from contextlib import asynccontextmanager


logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.api.agent import router as agent_router
from app.api.auth import router as auth_router
from app.api.gaps import router as gaps_router
from app.api.graph import router as graph_router
from app.api.ingest import router as ingest_router
from app.api.metrics import router as metrics_router
from app.api.search import router as search_router
from app.api.summarize import router as summarize_router
from app.core.config import settings
from app.core.limiter import limiter

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    import asyncio

    from app.db.database import init_db
    from app.services.graph_schema import ensure_schema

    try:
        await init_db()
    except Exception:
        logger.warning(
            "Could not initialize Postgres on startup - auth features will fail until it's reachable."
        )

    async def _setup_graph_schema():
        # Runs in the background so a slow Neo4j connection never delays startup.
        try:
            await asyncio.wait_for(ensure_schema(), timeout=120.0)
            logger.info("Neo4j schema is ready.")
        except Exception:
            logger.warning(
                "Neo4j schema setup did not finish - graph features may fail until it's reachable."
            )

    schema_task = asyncio.create_task(_setup_graph_schema())
    yield
    schema_task.cancel()


app = FastAPI(title="Research Mate API", version="0.1.0", lifespan=lifespan)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def track_metrics_middleware(request, call_next):
    from app.services.metrics import record_failure, record_request

    endpoint = request.url.path
    record_request(endpoint)
    response = await call_next(request)
    if response.status_code >= 400:
        record_failure(endpoint)
    return response

app.include_router(search_router, prefix="/api", tags=["search"])
app.include_router(ingest_router, prefix="/api", tags=["ingest"])
app.include_router(summarize_router, prefix="/api", tags=["summarize"])
app.include_router(agent_router, prefix="/api", tags=["agent"])
app.include_router(graph_router, prefix="/api", tags=["graph"])
app.include_router(gaps_router, prefix="/api", tags=["gaps"])
app.include_router(auth_router, prefix="/api", tags=["auth"])
app.include_router(metrics_router, prefix="/api", tags=["metrics"])


@app.get("/health")
def health_check():
    """Confirms the app is up and which environment it's configured for."""
    return {"status": "ok", "env": settings.app_env}


if __name__ == "__main__":
    import os

    import uvicorn

    port = int(os.environ.get("PORT", settings.app_port))
    uvicorn.run("app.main:app", host=settings.app_host, port=port, reload=False)