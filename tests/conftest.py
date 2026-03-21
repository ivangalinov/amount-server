from __future__ import annotations

import models  # noqa: F401 — регистрация всех моделей в Base.metadata
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from category.router import router as category_router
from database import Base, get_db
from workspace.model import Workspace


@pytest_asyncio.fixture
async def engine():
    eng = create_async_engine(
        "sqlite+aiosqlite://",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield eng
    await eng.dispose()


@pytest_asyncio.fixture
async def session_factory(engine):
    return async_sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


@pytest_asyncio.fixture
async def app(session_factory):
    async def override_get_db():
        async with session_factory() as session:  # type: AsyncSession
            yield session

    application = FastAPI()
    application.include_router(category_router)
    application.dependency_overrides[get_db] = override_get_db
    return application


@pytest_asyncio.fixture
async def client(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest_asyncio.fixture
async def workspace_id(session_factory):
    async with session_factory() as session:
        ws = Workspace(name="Test workspace")
        session.add(ws)
        await session.commit()
        await session.refresh(ws)
        return ws.id
