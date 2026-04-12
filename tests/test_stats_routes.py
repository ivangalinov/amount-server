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
async def test_dashboard_stats_aggregates(authenticated_client, workspace_id):
    food = (
        await authenticated_client.post(
            "/category", json=category_json(workspace_id, name="Food", type="expense")
        )
    ).json()["id"]
    salary = (
        await authenticated_client.post(
            "/category",
            json=category_json(
                workspace_id, name="Salary", type="income", color="#00aa00"
            ),
        )
    ).json()["id"]

    await authenticated_client.post(
        "/operation",
        json={
            "workspace_id": workspace_id,
            "category_id": food,
            "title": "Lunch",
            "amount": -300,
            "created": "2025-03-10T12:00:00+00:00",
        },
    )
    await authenticated_client.post(
        "/operation",
        json={
            "workspace_id": workspace_id,
            "category_id": food,
            "title": "Dinner",
            "amount": -200,
            "created": "2025-03-11T18:00:00+00:00",
        },
    )
    await authenticated_client.post(
        "/operation",
        json={
            "workspace_id": workspace_id,
            "category_id": salary,
            "title": "Pay",
            "amount": 5000,
            "created": "2025-03-15T10:00:00+00:00",
        },
    )

    r = await authenticated_client.get(
        "/stats/dashboard",
        params={
            "workspace_id": workspace_id,
            "date_from": "2025-03-01T00:00:00Z",
            "date_to": "2025-03-31T23:59:59Z",
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert body["balance"] == 4500
    assert body["total_income"] == 5000
    assert body["total_expense"] == -500
    assert len(body["expenses_by_category"]) == 1
    assert body["expenses_by_category"][0]["category_id"] == food
    assert body["expenses_by_category"][0]["sum"] == -500
    assert body["expenses_by_category"][0]["name"] == "Food"
    assert len(body["income_by_category"]) == 1
    assert body["income_by_category"][0]["sum"] == 5000
    days = {d["day"]: d["sum"] for d in body["expenses_by_day"]}
    assert days.get("2025-03-10") == -300
    assert days.get("2025-03-11") == -200
    months = {m["month"]: m["sum"] for m in body["expenses_by_month"]}
    assert months.get("2025-03") == -500


@pytest.mark.asyncio
async def test_dashboard_stats_forbidden_foreign_workspace(
    authenticated_client, session_factory, workspace_id
):
    async with session_factory() as session:
        from workspace.model import Workspace

        ws = Workspace(name="Other")
        session.add(ws)
        await session.commit()
        await session.refresh(ws)
        foreign = ws.id

    r = await authenticated_client.get(
        "/stats/dashboard",
        params={
            "workspace_id": foreign,
            "date_from": "2025-01-01T00:00:00Z",
            "date_to": "2025-12-31T23:59:59Z",
        },
    )
    assert r.status_code == 403
