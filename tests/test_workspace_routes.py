from fastapi import HTTPException
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, select
from workspace import WorkspaceUser, Workspace
from fastapi import APIRouter, Depends, HTTPException, Query, status

@pytest.mark.asyncio
async def test_get_active_workspace(client: AsyncClient, session_factory):
    [user] = await create_users(
        client,
        {"email": "bodsadb@test.dev", "password": "password123"}
    )

    
    async with session_factory() as s:
        w_u = (
            await s.execute(
                select(WorkspaceUser).select_from(WorkspaceUser).where(
                    WorkspaceUser.user_id == user['id']
                )
            )
        ).scalar_one()

        wp = (
            await s.execute(
                select(Workspace).where(Workspace.id == w_u.workspace_id)
            )
        ).scalar_one()

    response = await client.get('/workspace/active')
    assert response.status_code == status.HTTP_200_OK

    result = response.json()
    assert result['id'] == wp.id
    assert result['name'] == wp.name


@pytest.mark.asyncio
async def test_get_user_workspace(client: AsyncClient, session_factory):

    users = await create_users(
        client,
        {"email": "jim@test.dev", "password": "password123"},
        {"email": "bob@test.dev", "password": "password123"}
    )
    
    user = users[1]
    

    async with session_factory() as s:
        wp = (
            await s.execute(
                select(WorkspaceUser.workspace_id).select_from(WorkspaceUser).where(
                    WorkspaceUser.user_id == user['id']
                )
            )
        ).scalar_one()

    print(wp)

    response = await client.get('/workspace/users', params={
        'workspace_id': wp
    })
    assert response.status_code == 200
    items = response.json()['items']

    assert len(items) == 1
    assert items[0]['id'] == user['id']
    assert items[0]['name'] == user['email'].split('@')[0]


@pytest.mark.asyncio
async def test_get_another_users_workspace(client: AsyncClient, session_factory):
    users = await create_users(
        client,
        {"email": "dsad@test.dev", "password": "password123"},
        {"email": "bodsadb@test.dev", "password": "password123"}
    )
    
    user = users[0]
    
    async with session_factory() as s:
        wp = (
            await s.execute(
                select(WorkspaceUser.workspace_id).select_from(WorkspaceUser).where(
                    WorkspaceUser.user_id == user['id']
                )
            )
        ).scalar_one()

    response = await client.get('/workspace/users', params={
        'workspace_id': wp
    })
    assert response.status_code == status.HTTP_403_FORBIDDEN


async def create_users(client: AsyncClient, *payload: tuple[dict]) -> list[dict]:
    created = []

    for data in payload:
        new_user = await client.post(
            "/auth/register",
            json={"email": data['email'], "password": data['password'] or '123'},
        )
        created.append({
            'id': new_user.json()['id'],
            'email': data['email']
        })
    return created