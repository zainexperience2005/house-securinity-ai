"""FastAPI production entrypoint for House Scrutiny AI.

Initializes the FastAPI application, mounts modular routers for drawing scrutiny,
bylaws, review cases, thread memories, and AI model catalogs, and configures
CORS and structured request logging.
"""

import logging
import sys
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from src.api.routers import cases, models, reports, scrutinize, threads
from src.config.settings import settings
from src.memory.database import run_migrations

# Configure structured application logger
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[logging.StreamHandler(sys.stdout)],
    force=True,
)
logger = logging.getLogger("house_scrutiny.api")

# Ensure uvicorn's own loggers route directly to stdout
for _u_name in ("uvicorn", "uvicorn.access", "uvicorn.error"):
    _ulog = logging.getLogger(_u_name)
    _ulog.handlers = [logging.StreamHandler(sys.stdout)]
    _ulog.propagate = False


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Run Alembic migrations once at startup, check Redis cache, and serve requests."""
    run_migrations()

    # Seed AI models catalog if the table is empty
    try:
        from src.memory.models_store import init_models_table

        init_models_table()
    except Exception as _e:
        logger.warning(f"Could not seed AI models catalog: {_e}")

    # Check Redis cache connectivity on startup
    try:
        from src.memory.cache import get_redis

        get_redis()
    except Exception as _err:
        logger.warning(f"[REDIS] Initialization check failed: {_err}")

    logger.info("🏛️ House Scrutiny API ready to receive requests.")
    sys.stdout.flush()
    yield
    logger.info("🛑 House Scrutiny API shutting down.")


# Initialize FastAPI App
app = FastAPI(
    title="🏛️ House Scrutiny AI Backend",
    description="Production REST API for Architectural & Structural Drawing Verification and Municipal Bylaw Audits.",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# Enable CORS for frontend integrations (Next.js, Vercel, React, Mobile)
configured_origins = [o.strip() for o in settings.frontend_url.split(",") if o.strip()]
default_origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:3001",
    "http://127.0.0.1:3001",
    "http://localhost:8000",
    "http://127.0.0.1:8000",
]
allowed_origins = list(dict.fromkeys(configured_origins + default_origins))

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1)(:[0-9]+)?$|^https://.*\.vercel\.app$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)


@app.middleware("http")
async def log_requests_middleware(request: Request, call_next):
    """Log every incoming endpoint request, status code, and elapsed time."""
    start_time = time.perf_counter()
    response = await call_next(request)
    duration_ms = (time.perf_counter() - start_time) * 1000

    status = response.status_code
    method = request.method
    path = request.url.path

    symbol = "🟢" if status < 400 else "🟡" if status < 500 else "🔴"
    msg = f"{symbol} {method} {path} -> {status} ({duration_ms:.1f}ms)"
    logger.info(msg)
    print(msg, flush=True)
    return response


# ==============================================================================
# CORE SERVICE DISCOVERY & HEALTH
# ==============================================================================
@app.get("/", tags=["General"])
async def root():
    """Service discovery: name, version, and primary route map."""
    return {
        "service": "House Scrutiny AI Agent API",
        "version": "2.0.0",
        "status": "online",
        "documentation": "/docs",
        "endpoints": {
            "scrutinize": "/api/v1/scrutinize",
            "scrutinize_stream": "/api/v1/scrutinize/stream",
            "scrutinize_package": "/api/v1/scrutinize/package",
            "pdf_report": "/api/v1/reports/pdf",
            "cases": "/api/v1/cases/{case_id}",
            "bylaws": "/api/v1/bylaws",
            "threads": "/api/v1/threads",
            "models": "/api/v1/models",
        },
    }


@app.get("/health", tags=["General"])
async def health_check():
    """Liveness probe plus configured OPENAI_MODEL."""
    return {
        "status": "healthy",
        "timestamp": time.time(),
        "openai_model": settings.openai_model,
        "typesafe_connected": True,
    }


# ==============================================================================
# MOUNT MODULAR ROUTERS
# ==============================================================================
app.include_router(scrutinize.router)
app.include_router(cases.router)
app.include_router(reports.router)
app.include_router(threads.router)
app.include_router(models.router)
