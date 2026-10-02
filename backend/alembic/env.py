"""Alembic migration environment for House Scrutiny AI.

Uses the existing psycopg DATABASE_URL from src.config.settings — no SQLAlchemy ORM.
Runs offline (generates SQL) or online (executes against Neon PostgreSQL).
"""
import os
import sys
from logging.config import fileConfig

from alembic import context

# Allow imports from the backend src package
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from src.config.settings import settings  # noqa: E402

# Alembic Config object — provides access to alembic.ini values
config = context.config

# Set up logging from alembic.ini only if invoked via CLI, not inside FastAPI
if config.config_file_name is not None and "uvicorn" not in sys.modules:
    try:
        fileConfig(config.config_file_name, disable_existing_loggers=False)
    except Exception:
        pass

# Override the sqlalchemy.url with the real DATABASE_URL from settings
# Convert psycopg DSN to SQLAlchemy URL format (psycopg3 driver)
_db_url = settings.database_url or os.getenv("DATABASE_URL", "")
# Ensure we use the psycopg (v3) SQLAlchemy dialect
if _db_url.startswith("postgresql://"):
    _db_url = _db_url.replace("postgresql://", "postgresql+psycopg://", 1)
elif _db_url.startswith("postgres://"):
    _db_url = _db_url.replace("postgres://", "postgresql+psycopg://", 1)

config.set_main_option("sqlalchemy.url", _db_url)

# We don't use declarative metadata (no ORM models), so target_metadata is None.
# Alembic will not auto-generate diffs — migrations are hand-written.
target_metadata = None


def run_migrations_offline() -> None:
    """Emit SQL to stdout — useful for review without a live DB connection."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Connect to the live Neon DB and apply pending migrations."""
    from sqlalchemy import create_engine, pool

    connectable = create_engine(
        config.get_main_option("sqlalchemy.url"),
        poolclass=pool.NullPool,  # No pooling — Neon manages its own
        connect_args={"sslmode": "require"},
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
