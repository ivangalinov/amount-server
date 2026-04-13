from __future__ import annotations

import pytest


def category_json(workspace_id: int, **overrides):
    data = {
        "name": "Cat",
        "workspace_id": workspace_id,
        "type": "expense",
        "color": "#112233",
    }
    data.update(overrides)
    return data


@pytest.mark.asyncio
async def test_create_operation(authenticated_client, workspace_id):
    cid = (
        await authenticated_client.post(
            "/category", json=category_json(workspace_id, name="Food")
        )
    ).json()["id"]

    r = await authenticated_client.post(
        "/operation",
        json={
            "workspace_id": workspace_id,
            "category_id": cid,
            "title": "Обед",
            "amount": -500,
        },
    )
    assert r.status_code == 201
    body = r.json()
    assert body["title"] == "Обед"
    assert body["amount"] == -500
    assert body["category_id"] == cid
    assert body["workspace_id"] == workspace_id
    assert "user_id" in body
    assert "created" in body

@pytest.mark.asyncio
async def test_create_operation_with_expence_category(authenticated_client, workspace_id):
    cid = (
        await authenticated_client.post(
            "/category", json=category_json(workspace_id, name="Food")
        )
    ).json()["id"]

    r = await authenticated_client.post(
        "/operation",
        json={
            "workspace_id": workspace_id,
            "category_id": cid,
            "title": "Обед",
            "amount": 500,
        },
    )
    assert r.status_code == 201
    body = r.json()
    assert body["title"] == "Обед"
    assert body["amount"] == -500
    assert body["category_id"] == cid
    assert body["workspace_id"] == workspace_id
    assert "user_id" in body
    assert "created" in body


@pytest.mark.asyncio
async def test_create_operation_with_income_category(authenticated_client, workspace_id):
    cid = (
        await authenticated_client.post(
            "/category", json=category_json(workspace_id, name="Food", type='income')
        )
    ).json()["id"]

    r = await authenticated_client.post(
        "/operation",
        json={
            "workspace_id": workspace_id,
            "category_id": cid,
            "title": "Обед",
            "amount": 500,
        },
    )
    assert r.status_code == 201
    body = r.json()
    assert body["title"] == "Обед"
    assert body["amount"] == 500
    assert body["category_id"] == cid
    assert body["workspace_id"] == workspace_id
    assert "user_id" in body
    assert "created" in body


@pytest.mark.asyncio
async def test_list_operations_filter_and_total(authenticated_client, workspace_id):
    cid = (
        await authenticated_client.post(
            "/category", json=category_json(workspace_id, name="A")
        )
    ).json()["id"]
    await authenticated_client.post(
        "/operation",
        json={
            "workspace_id": workspace_id,
            "category_id": cid,
            "title": "One",
            "amount": 100,
        },
    )
    await authenticated_client.post(
        "/operation",
        json={
            "workspace_id": workspace_id,
            "category_id": cid,
            "title": "Two",
            "amount": -50,
        },
    )

    r = await authenticated_client.get(
        "/operation", params={"workspace_id": workspace_id}
    )
    assert r.status_code == 200
    data = r.json()
    assert data["total"] == 2
    assert len(data["items"]) == 2
    assert data["items"][0]["title"] in ("Two", "One")  # desc by created

    r2 = await authenticated_client.get(
        "/operation",
        params={"workspace_id": workspace_id, "category_id": cid},
    )
    assert r2.json()["total"] == 2


@pytest.mark.asyncio
async def test_operation_forbidden_foreign_workspace(
    authenticated_client, session_factory, workspace_id
):
    async with session_factory() as session:
        from workspace.model import Workspace

        ws = Workspace(name="Other")
        session.add(ws)
        await session.commit()
        await session.refresh(ws)
        foreign = ws.id

    cid = (
        await authenticated_client.post(
            "/category", json=category_json(workspace_id)
        )
    ).json()["id"]
    r = await authenticated_client.post(
        "/operation",
        json={
            "workspace_id": foreign,
            "category_id": cid,
            "title": "X",
            "amount": 1,
        },
    )
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_operation_category_wrong_workspace(authenticated_client, session_factory):
    """Категория из другого workspace — 404."""
    async with session_factory() as session:
        from workspace.model import Workspace
        from user.model import User
        from auth.security import hash_password
        from workspace.model import WorkspaceUser
        from category.model import Category, CategoryType

        u = User(
            email="op2@test.dev",
            name="U",
            password_hash=hash_password("pw"),
        )
        ws_a = Workspace(name="A")
        ws_b = Workspace(name="B")
        session.add_all([u, ws_a, ws_b])
        await session.flush()
        session.add_all(
            [
                WorkspaceUser(user_id=u.id, workspace_id=ws_a.id),
                WorkspaceUser(user_id=u.id, workspace_id=ws_b.id),
            ]
        )
        cat_b = Category(
            name="OnlyB",
            workspace_id=ws_b.id,
            type=CategoryType.EXPENSE,
            color="#000000",
            user_id=u.id,
        )
        session.add(cat_b)
        await session.commit()
        wid_a, wid_b, cat_id = ws_a.id, ws_b.id, cat_b.id

    client = authenticated_client
    await client.post("/auth/login", json={"email": "op2@test.dev", "password": "pw"})

    r = await client.post(
        "/operation",
        json={
            "workspace_id": wid_a,
            "category_id": cat_id,
            "title": "bad",
            "amount": 1,
        },
    )
    assert r.status_code == 404
    assert r.json()["detail"] == "Category not found"


@pytest.mark.asyncio
async def test_patch_and_delete_operation(authenticated_client, workspace_id):
    cid = (
        await authenticated_client.post(
            "/category", json=category_json(workspace_id)
        )
    ).json()["id"]
    created = (
        await authenticated_client.post(
            "/operation",
            json={
                "workspace_id": workspace_id,
                "category_id": cid,
                "title": "Old",
                "amount": 10,
            },
        )
    ).json()
    oid = created["id"]

    pr = await authenticated_client.patch(
        f"/operation/{oid}",
        json={"title": "New", "amount": -99},
    )
    assert pr.status_code == 200
    assert pr.json()["title"] == "New"
    assert pr.json()["amount"] == -99

    dr = await authenticated_client.delete(f"/operation/{oid}")
    assert dr.status_code == 204

    gr = await authenticated_client.get(f"/operation/{oid}")
    assert gr.status_code == 404

@pytest.mark.asyncio
async def test_patch_expense_category(authenticated_client, workspace_id):
    cid = (
        await authenticated_client.post(
            "/category", json=category_json(workspace_id)
        )
    ).json()["id"]
    created = (
        await authenticated_client.post(
            "/operation",
            json={
                "workspace_id": workspace_id,
                "category_id": cid,
                "title": "Old",
                "amount": -10,
            },
        )
    ).json()
    oid = created["id"]

    pr = await authenticated_client.patch(
        f"/operation/{oid}",
        json={"title": "New", "amount": 99},
    )
    assert pr.status_code == 200
    assert pr.json()["title"] == "New"
    assert pr.json()["amount"] == -99

    dr = await authenticated_client.delete(f"/operation/{oid}")
    assert dr.status_code == 204

    gr = await authenticated_client.get(f"/operation/{oid}")
    assert gr.status_code == 404
