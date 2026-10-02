"""src/memory/database.py - Neon PostgreSQL Connection & Alembic Migration Runner.

Provides resilient connection handling and runs Alembic migrations exactly
once at application startup.  The old ad-hoc `init_database_tables()` that
called CREATE TABLE IF NOT EXISTS on every single request has been removed.
"""

import logging
import os
from contextlib import contextmanager

try:
    import psycopg
except ImportError:
    psycopg = None

from src.config.settings import settings

logger = logging.getLogger(__name__)

# Default Neon connection URL (overridden by DATABASE_URL env var / settings)
DEFAULT_DATABASE_URL = (
    "postgresql://neondb_owner:npg_3OK9dMfVaUkb@"
    "ep-shiny-breeze-b4r10ing-pooler.c-6.us-east-2.aws.neon.tech/neondb"
    "?sslmode=require&channel_binding=require"
)

# Guard: run Alembic migrations at most once per process lifetime
_MIGRATIONS_RAN: bool = False


def get_database_url() -> str:
    """Retrieve active database URL from settings or environment."""
    url = settings.database_url or os.getenv("DATABASE_URL") or DEFAULT_DATABASE_URL
    return url.strip()


@contextmanager
def get_db_connection(timeout: int = 10):
    """Context manager yielding a live psycopg connection to Neon DB.

    Automatically commits on normal exit and rolls back on exception.
    """
    if psycopg is None:
        raise RuntimeError("psycopg is not installed. Install psycopg[binary] for PostgreSQL memory.")

    db_url = get_database_url()
    conn = None
    try:
        conn = psycopg.connect(db_url, connect_timeout=timeout)
        yield conn
        conn.commit()
    except Exception as exc:
        if conn:
            conn.rollback()
        logger.warning(f"Neon DB connection error: {exc}")
        raise
    finally:
        if conn and not conn.closed:
            conn.close()


def run_migrations() -> bool:
    """Apply all pending Alembic migrations against Neon PostgreSQL.

    Safe to call on every app startup — Alembic tracks applied revisions in
    the ``alembic_version`` table and skips already-applied ones.
    Only executes once per process (guarded by _MIGRATIONS_RAN).
    """
    global _MIGRATIONS_RAN
    if _MIGRATIONS_RAN:
        return True

    try:
        import os as _os

        from alembic.config import Config

        from alembic import command

        # Locate alembic.ini relative to this file's backend root
        backend_root = _os.path.dirname(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
        alembic_cfg_path = _os.path.join(backend_root, "alembic.ini")

        cfg = Config(alembic_cfg_path)
        # Override the URL at runtime so alembic.ini never holds real credentials
        db_url = get_database_url()
        if db_url.startswith("postgresql://"):
            db_url = db_url.replace("postgresql://", "postgresql+psycopg://", 1)
        elif db_url.startswith("postgres://"):
            db_url = db_url.replace("postgres://", "postgresql+psycopg://", 1)
        cfg.set_main_option("sqlalchemy.url", db_url)
        # Tell Alembic where the migration scripts live
        cfg.set_main_option(
            "script_location",
            _os.path.join(backend_root, "alembic"),
        )

        # Mute repetitive Alembic and autogenerate plugin debug logs
        logging.getLogger("alembic").setLevel(logging.WARNING)
        logging.getLogger("alembic.runtime").setLevel(logging.WARNING)
        logging.getLogger("alembic.runtime.plugins").setLevel(logging.WARNING)
        logging.getLogger("alembic.runtime.migration").setLevel(logging.WARNING)

        command.upgrade(cfg, "head")
        _MIGRATIONS_RAN = True
        logger.info("Database schema up to date.")
        return True

    except Exception as exc:
        logger.error(f"Alembic migration failed: {exc}", exc_info=True)
        # Non-fatal: fall through — the DB likely already has the schema
        _MIGRATIONS_RAN = True  # Don't retry every request on persistent failure
        return False


# ---------------------------------------------------------------------------
# Backward-compatibility stub — kept so any stale import doesn't hard-crash.
# Delegates to run_migrations() but logs a deprecation warning.
# ---------------------------------------------------------------------------
def init_database_tables() -> bool:
    """Deprecated: use run_migrations() instead.
    `
        Retained for backward compatibility with any code paths that still call
        this function.  Internally delegates to run_migrations() which is guarded
        against re-running within the same process.
    """
    logger.debug(
        "init_database_tables() is deprecated — schema is now managed by "
        "Alembic. Call run_migrations() at startup instead."
    )
    return run_migrations()
