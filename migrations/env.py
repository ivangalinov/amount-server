from logging.config import fileConfig
import os

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import AsyncEngine, async_engine_from_config

from database import Base, DATABASE_URL
import models  # noqa: F401  регистрируем все модели в Base.metadata

_sql_echo = os.getenv("SQL_ECHO", "true").strip().lower() in ("1", "true", "yes", "on")

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Используем тот же URL, что и приложение (из database.py / DATABASE_URL)
config.set_main_option("sqlalchemy.url", DATABASE_URL)

# Interpret the config file for Python logging.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Метаданные моделей для autogenerate
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_sync_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode with async engine."""
    section = dict(config.get_section(config.config_ini_section, {}) or {})
    if _sql_echo:
        section["sqlalchemy.echo"] = "true"
    connectable = async_engine_from_config(
        section,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    assert isinstance(connectable, AsyncEngine)

    async def do_run_migrations() -> None:
        async with connectable.connect() as connection:
            await connection.run_sync(run_sync_migrations)

    import asyncio

    asyncio.run(do_run_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

