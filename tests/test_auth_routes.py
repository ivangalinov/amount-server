from __future__ import annotations

import pytest
from sqlalchemy import func, select

from auth.security import hash_password
from user.model import User
from workspace.model import Workspace, WorkspaceUser


@pytest.mark.asyncio
async def test_register_creates_default_workspace(client, session_factory):
    r = await client.post(
        "/auth/register",
        json={
            "email": "wsreg@test.dev",
            "password": "password123",
            "name": "RegUser",
        },
    )
    assert r.status_code == 201
    uid = r.json()["id"]
    async with session_factory() as s:
        n = (
            await s.execute(
                select(func.count()).select_from(WorkspaceUser).where(
                    WorkspaceUser.user_id == uid
                )
            )
        ).scalar_one()
        assert n == 1
        ws_name = (
            await s.execute(
                select(Workspace.name)
                .join(WorkspaceUser, WorkspaceUser.workspace_id == Workspace.id)
                .where(WorkspaceUser.user_id == uid)
            )
        ).scalar_one()
        assert "RegUser" in ws_name


@pytest.mark.asyncio
async def test_register_sets_cookie_and_returns_user(client):
    r = await client.post(
        "/auth/register",
        json={
            "email": "Alice@Example.COM",
            "password": "password123",
            "name": "Alice",
        },
    )
    assert r.status_code == 201
    body = r.json()
    assert body["email"] == "alice@example.com"
    assert body["name"] == "Alice"
    assert "id" in body
    assert "access_token" in r.cookies


@pytest.mark.asyncio
async def test_register_duplicate_email(client):
    payload = {"email": "dup@test.dev", "password": "password123", "name": "One"}
    assert (await client.post("/auth/register", json=payload)).status_code == 201
    r = await client.post("/auth/register", json=payload)
    assert r.status_code == 409
    assert r.json()["detail"] == "Email already registered"


@pytest.mark.asyncio
async def test_register_name_defaults_to_local_part(client):
    r = await client.post(
        "/auth/register",
        json={"email": "bob@test.dev", "password": "password123"},
    )
    assert r.status_code == 201
    assert r.json()["name"] == "bob"
    assert r.json()["email"] == "bob@test.dev"


@pytest.mark.asyncio
async def test_login_creates_workspace_when_user_had_none(client, session_factory):
    async with session_factory() as s:
        u = User(
            email="legacyws@test.dev",
            name="Legacy",
            password_hash=hash_password("secretpass"),
        )
        s.add(u)
        await s.commit()
        await s.refresh(u)
        uid = u.id

    r = await client.post(
        "/auth/login",
        json={"email": "legacyws@test.dev", "password": "secretpass"},
    )
    assert r.status_code == 200
    async with session_factory() as s:
        n = (
            await s.execute(
                select(func.count()).select_from(WorkspaceUser).where(
                    WorkspaceUser.user_id == uid
                )
            )
        ).scalar_one()
        assert n == 1


@pytest.mark.asyncio
async def test_login_success(client):
    await client.post(
        "/auth/register",
        json={"email": "login@test.dev", "password": "secretpass", "name": "L"},
    )
    r = await client.post(
        "/auth/login",
        json={"email": "login@test.dev", "password": "secretpass"},
    )
    assert r.status_code == 200
    assert r.json()["email"] == "login@test.dev"
    assert "access_token" in r.cookies


@pytest.mark.asyncio
async def test_login_wrong_password(client):
    await client.post(
        "/auth/register",
        json={"email": "u2@test.dev", "password": "rightpassword", "name": "U"},
    )
    r = await client.post(
        "/auth/login",
        json={"email": "u2@test.dev", "password": "wrongpassword"},
    )
    assert r.status_code == 401
    assert r.json()["detail"] == "Invalid email or password"


@pytest.mark.asyncio
async def test_me_requires_cookie(client):
    r = await client.get("/auth/me")
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_me_with_session(client):
    await client.post(
        "/auth/register",
        json={"email": "me@test.dev", "password": "password123", "name": "Me"},
    )
    r = await client.get("/auth/me")
    assert r.status_code == 200
    assert r.json()["email"] == "me@test.dev"
    assert r.json()["name"] == "Me"


@pytest.mark.asyncio
async def test_logout_clears_session(client):
    await client.post(
        "/auth/register",
        json={"email": "out@test.dev", "password": "password123", "name": "O"},
    )
    assert (await client.get("/auth/me")).status_code == 200

    r = await client.post("/auth/logout")
    assert r.status_code == 204

    assert (await client.get("/auth/me")).status_code == 401
