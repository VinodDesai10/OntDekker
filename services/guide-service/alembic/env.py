import asyncio
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import async_engine_from_config
from alembic import context

from app.config.settings import settings
from shared import Base

# ---------------------------------------------------------------------------
# CRITICAL: Import all ORM models so they register against Base.metadata
# before target_metadata is assigned below.
#
# Without this import, Base.metadata contains zero tables and Alembic
# autogenerate produces a completely empty migration.
#
# app/models/__init__.py imports every model module in dependency order,
# so importing the package is sufficient to register all 7 tables.
# ---------------------------------------------------------------------------
import app.models  # noqa: F401  — side-effect import, must not be removed

# Alembic Config object
config = context.config

# NOTE: We do NOT call fileConfig() here. The project uses
# shared.logging.setup_logging() for structured JSON logging.
# The minimal alembic.ini does not contain the [loggers]/[handlers]/
# [formatters] sections that fileConfig() requires, and Alembic
# falls back to Python's default logging without it.

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = settings.DATABASE_URL
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)

    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    configuration = config.get_section(config.config_ini_section) or {}
    configuration["sqlalchemy.url"] = settings.DATABASE_URL

    connectable = async_engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
