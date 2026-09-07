import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.database import get_engine, get_sessionmaker, Base
from app.api import health, processes, blueprints, ingestion, weights, audit, catalog
from app.seed import seed_database
from app.config import get_settings

logger = logging.getLogger(__name__)

BACKEND_DIR = Path(__file__).resolve().parent.parent


def _run_migrations() -> None:
    """Apply Alembic migrations. Runs in a thread — Alembic is synchronous."""
    from alembic import command
    from alembic.config import Config

    cfg = Config(str(BACKEND_DIR / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
    command.upgrade(cfg, "head")

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("KINTIX API starting")
    settings = get_settings()

    # Schema comes from Alembic so dev and production converge on one migration
    # history. create_all remains only for throwaway test databases, where a
    # migration run would add nothing.
    if settings.RUN_MIGRATIONS_ON_STARTUP:
        await asyncio.to_thread(_run_migrations)
        logger.info("Alembic migrations applied")
    else:
        async with get_engine().begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    if settings.SEED_DEMO_DATA:
        async with get_sessionmaker()() as session:
            await seed_database(session)
        logger.info("Demo catalog seeded")

    yield

    logger.info("KINTIX API shutting down")
    await get_engine().dispose()

settings = get_settings()

app = FastAPI(
    title="KINTIX API",
    description="AI-Powered Work Intelligence — Automation Opportunity Miner",
    version=settings.API_VERSION,
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    """Log the traceback (otherwise invisible with uvicorn --reload) and return a
    JSON body so the frontend can surface a real message instead of an opaque
    network error."""
    logger.exception("Unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


app.include_router(health.router)
app.include_router(processes.router, prefix="/api")
app.include_router(blueprints.router, prefix="/api")
app.include_router(ingestion.router, prefix="/api")
app.include_router(weights.router, prefix="/api")
app.include_router(audit.router, prefix="/api")
app.include_router(catalog.router, prefix="/api")
