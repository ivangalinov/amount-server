from __future__ import annotations
import pytest


def category_payload(workspace_id: int, **overrides):
    data = {
        "name": "Food",
        "workspace_id": workspace_id,
        "type": "expense",
        "color": "#112233",
    }
    data.update(overrides)
    return data


@pytest.mark.asyncio
async def test_create_category(client, workspace_id):
    r = await client.post("/category", json=category_payload(workspace_id))
    assert r.status_code == 201
    body = r.json()
    assert body["name"] == "Food"
    assert body["type"] == "expense"
    assert body["color"] == "#112233"
    assert body["limit"] is None
    assert "id" in body


@pytest.mark.asyncio
async def test_get_categories_empty(client):
    r = await client.get("/category")
    assert r.status_code == 200
    data = r.json()
    assert data["items"] == []
    assert data["total"] == 10


@pytest.mark.asyncio
async def test_get_categories_filter_by_type(client, workspace_id):
    await client.post("/category", json=category_payload(workspace_id, type="income"))
    await client.post("/category", json=category_payload(workspace_id, name="Other", type="expense"))

    r = await client.get("/category", params={"type": "income"})
    assert r.status_code == 200
    items = r.json()["items"]
    assert len(items) == 1
    assert items[0]["name"] == "Food"
    assert items[0]["type"] == "income"


@pytest.mark.asyncio
async def test_get_category_by_id(client, workspace_id):
    created = (await client.post("/category", json=category_payload(workspace_id))).json()
    cid = created["id"]

    r = await client.get(f"/category/{cid}")
    assert r.status_code == 200
    body = r.json()
    assert body["id"] == cid
    assert body["name"] == "Food"
    assert body["type"] == "expense"


@pytest.mark.asyncio
async def test_get_category_not_found(client):
    r = await client.get("/category/99999")
    assert r.status_code == 404
    assert r.json()["detail"] == "Category not found"


@pytest.mark.asyncio
async def test_update_category(client, workspace_id):
    created = (await client.post("/category", json=category_payload(workspace_id))).json()
    cid = created["id"]

    r = await client.patch(f"/category/{cid}", json={"name": "Updated", "color": "#000000"})
    assert r.status_code == 200
    body = r.json()
    assert body["name"] == "Updated"
    assert body["color"] == "#000000"
    assert body["type"] == "expense"


@pytest.mark.asyncio
async def test_update_category_not_found(client):
    r = await client.patch("/category/99999", json={"name": "X"})
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_delete_category(client, workspace_id):
    created = (await client.post("/category", json=category_payload(workspace_id))).json()
    cid = created["id"]

    r = await client.delete(f"/category/{cid}")
    assert r.status_code == 204
    assert r.content == b""

    r2 = await client.get(f"/category/{cid}")
    assert r2.status_code == 404


@pytest.mark.asyncio
async def test_delete_category_not_found(client):
    r = await client.delete("/category/99999")
    assert r.status_code == 404
