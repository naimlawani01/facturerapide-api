"""
Alembic environment configuration.
Uses SYNC engine (psycopg) for migrations, even though the app uses async SQLAlchemy.
This is because Alembic works better with sync engines, especially with Supabase/pgbouncer.
"""

from logging.config import fileConfig

from sqlalchemy import create_engine, pool
from sqlalchemy.engine import Connection

from alembic import context

# Import your models and config
from app.core.config import settings
from app.core.database import Base
from app.models import *  # noqa: Import all models for autogenerate

# Alembic Config object
config = context.config

# Set database URL from application settings
# Alembic needs a SYNC driver (psycopg), not async (asyncpg)
database_url = settings.DATABASE_URL_SYNC

# Convert asyncpg to psycopg if needed (Alembic requires sync driver)
if "+asyncpg" in database_url:
    database_url = database_url.replace("+asyncpg", "+psycopg")
elif "postgresql://" in database_url and "+" not in database_url:
    # If no driver specified, add psycopg
    database_url = database_url.replace("postgresql://", "postgresql+psycopg://")

# Use attributes to avoid ConfigParser interpolation issues with % in URL
config.attributes["sqlalchemy.url"] = database_url

# Also set in the main section for compatibility
try:
    config.set_main_option("sqlalchemy.url", database_url)
except ValueError:
    # If ConfigParser fails (due to % in password), that's OK - we use attributes
    pass

# Interpret the config file for Python logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Model's MetaData object for 'autogenerate' support
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """
    Run migrations in 'offline' mode.
    
    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well. By skipping the Engine creation
    we don't even need a DBAPI to be available.
    
    Calls to context.execute() here emit the given string to the
    script output.
    """
    # Get URL from attributes first (to avoid ConfigParser interpolation issues)
    url = config.attributes.get("sqlalchemy.url") or config.get_main_option("sqlalchemy.url") or database_url
    
    # Convert asyncpg to psycopg if needed
    if "+asyncpg" in url:
        url = url.replace("+asyncpg", "+psycopg")
    elif "postgresql://" in url and "+" not in url:
        url = url.replace("postgresql://", "postgresql+psycopg://")
    
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    """Run migrations with the given connection."""
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """
    Run migrations in 'online' mode with SYNC engine.
    
    We use a sync engine (psycopg) instead of async because:
    1. Alembic works better with sync engines
    2. Supabase uses pgbouncer which has issues with asyncpg prepared statements
    """
    # Get URL from attributes first
    url = config.attributes.get("sqlalchemy.url") or config.get_main_option("sqlalchemy.url") or database_url
    
    # Convert asyncpg to psycopg if needed
    if "+asyncpg" in url:
        url = url.replace("+asyncpg", "+psycopg")
    elif "postgresql://" in url and "+" not in url:
        url = url.replace("postgresql://", "postgresql+psycopg://")
    
    # Create SYNC engine (not async)
    connectable = create_engine(
        url,
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        do_run_migrations(connection)


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

