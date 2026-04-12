import os

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://postgres:postgres@localhost:5432/amount",
)

# Логирование всех SQL в stdout (уровень INFO у логгера sqlalchemy.engine).
# Отключить: SQL_ECHO=false
_sql_echo = os.getenv("SQL_ECHO", "true").strip().lower() in ("1", "true", "yes", "on")

engine = create_async_engine(DATABASE_URL, echo=_sql_echo, future=True)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    autoflush=False,
    expire_on_commit=False,
)


async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        yield session


async def init_db() -> None:
    """
    Создаёт таблицы по моделям, если их ещё нет.
    Безопасно вызывать много раз: существующие таблицы не трогаются.
    """
    # Импорт нужен, чтобы все модели зарегистрировались на Base.metadata
    import models  # noqa: F401

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


