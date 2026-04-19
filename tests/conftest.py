from __future__ import annotations

import os
import uuid

os.environ.setdefault(
    "JWT_SECRET",
    "pytest-jwt-secret-key-must-be-at-least-32-characters-long",
)

import models  # noqa: F401 — регистрация всех моделей в Base.metadata
import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from auth.router import router as auth_router
from auth.security import hash_password
from category.router import router as category_router
from operation.router import router as operation_router
from stats.router import router as stats_router
from workspace import router as wp_router
from database import Base, get_db
from user.model import User
from workspace.model import Workspace, WorkspaceUser


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
async def auth_session_data(session_factory):
    """Пользователь с паролем, workspace и членством — для логина в тестах категорий."""
    plain_password = "testpass123"
    email = f"cat_{uuid.uuid4().hex}@test.dev"
    async with session_factory() as session:
        u = User(
            email=email,
            name="Category Test User",
            password_hash=hash_password(plain_password),
        )
        ws = Workspace(name="Test workspace")
        session.add_all([u, ws])
        await session.flush()
        session.add(WorkspaceUser(user_id=u.id, workspace_id=ws.id))
        await session.commit()
        await session.refresh(ws)
        return {
            "email": u.email,
            "password": plain_password,
            "workspace_id": ws.id,
        }


@pytest_asyncio.fixture
async def app(session_factory):
    async def override_get_db():
        async with session_factory() as session:  # type: AsyncSession
            yield session

    application = FastAPI()
    application.include_router(auth_router)
    application.include_router(category_router)
    application.include_router(operation_router)
    application.include_router(stats_router)
    application.include_router(wp_router)
    application.dependency_overrides[get_db] = override_get_db
    return application


@pytest_asyncio.fixture
async def client(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest_asyncio.fixture
async def authenticated_client(client, auth_session_data):
    r = await client.post(
        "/auth/login",
        json={
            "email": auth_session_data["email"],
            "password": auth_session_data["password"],
        },
    )
    assert r.status_code == 200
    return client


@pytest.fixture
def workspace_id(auth_session_data):
    return auth_session_data["workspace_id"]
