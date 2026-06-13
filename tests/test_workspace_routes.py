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
async def test_get_active_workspace_after_joining_shared(client: AsyncClient, session_factory):
    users = await create_users(
        client,
        {"email": "shared-owner@test.dev", "password": "password123"},
        {"email": "shared-partner@test.dev", "password": "password123"},
    )
    owner, partner = users[0], users[1]

    async with session_factory() as s:
        owner_workspace_id = (
            await s.execute(
                select(WorkspaceUser.workspace_id).where(
                    WorkspaceUser.user_id == owner['id']
                )
            )
        ).scalar_one()
        shared_workspace = (
            await s.execute(
                select(Workspace).where(Workspace.id == owner_workspace_id)
            )
        ).scalar_one()

    await client.post(
        '/workspace/members',
        json={'workspace_id': owner_workspace_id, 'email': partner['email']},
    )

    await login_user(client, partner['email'], 'password123')
    response = await client.get('/workspace/active')
    assert response.status_code == status.HTTP_200_OK

    result = response.json()
    assert result['id'] == shared_workspace.id
    assert result['name'] == shared_workspace.name


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


@pytest.mark.asyncio
async def test_add_workspace_member_success(client: AsyncClient, session_factory):
    users = await create_users(
        client,
        {"email": "owner@test.dev", "password": "password123"},
        {"email": "partner@test.dev", "password": "password123"},
    )
    owner, partner = users[0], users[1]

    async with session_factory() as s:
        workspace_id = (
            await s.execute(
                select(WorkspaceUser.workspace_id).where(
                    WorkspaceUser.user_id == owner['id']
                )
            )
        ).scalar_one()

    response = await client.post(
        '/workspace/members',
        json={'workspace_id': workspace_id, 'email': partner['email']},
    )
    assert response.status_code == status.HTTP_201_CREATED
    body = response.json()
    assert body['workspace_id'] == workspace_id
    assert body['user_id'] == partner['id']
    assert body['email'] == partner['email']

    await login_user(client, owner['email'], 'password123')
    members = await client.get('/workspace/users', params={'workspace_id': workspace_id})
    assert members.status_code == status.HTTP_200_OK
    member_ids = [item['id'] for item in members.json()['items']]
    assert owner['id'] in member_ids
    assert partner['id'] in member_ids


@pytest.mark.asyncio
async def test_add_workspace_member_form_data(client: AsyncClient, session_factory):
    users = await create_users(
        client,
        {"email": "form-owner@test.dev", "password": "password123"},
        {"email": "form-partner@test.dev", "password": "password123"},
    )
    owner, partner = users[0], users[1]

    async with session_factory() as s:
        workspace_id = (
            await s.execute(
                select(WorkspaceUser.workspace_id).where(
                    WorkspaceUser.user_id == owner['id']
                )
            )
        ).scalar_one()

    response = await client.post(
        '/workspace/members',
        data={'workspace_id': str(workspace_id), 'email': partner['email']},
    )
    assert response.status_code == status.HTTP_201_CREATED
    assert response.json()['user_id'] == partner['id']


@pytest.mark.asyncio
async def test_add_workspace_member_unknown_workspace(client: AsyncClient):
    users = await create_users(
        client,
        {"email": "solo@test.dev", "password": "password123"},
    )

    response = await client.post(
        '/workspace/members',
        json={'workspace_id': 99999, 'email': users[0]['email']},
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
async def test_add_workspace_member_unknown_email(client: AsyncClient, session_factory):
    [owner] = await create_users(
        client,
        {"email": "lonely@test.dev", "password": "password123"},
    )

    async with session_factory() as s:
        workspace_id = (
            await s.execute(
                select(WorkspaceUser.workspace_id).where(
                    WorkspaceUser.user_id == owner['id']
                )
            )
        ).scalar_one()

    response = await client.post(
        '/workspace/members',
        json={'workspace_id': workspace_id, 'email': 'nobody@test.dev'},
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
async def test_add_workspace_member_already_member(client: AsyncClient, session_factory):
    users = await create_users(
        client,
        {"email": "host@test.dev", "password": "password123"},
        {"email": "guest@test.dev", "password": "password123"},
    )
    owner, guest = users[0], users[1]

    async with session_factory() as s:
        workspace_id = (
            await s.execute(
                select(WorkspaceUser.workspace_id).where(
                    WorkspaceUser.user_id == owner['id']
                )
            )
        ).scalar_one()

    payload = {'workspace_id': workspace_id, 'email': guest['email']}
    first = await client.post('/workspace/members', json=payload)
    assert first.status_code == status.HTTP_201_CREATED

    second = await client.post('/workspace/members', json=payload)
    assert second.status_code == status.HTTP_409_CONFLICT


async def login_user(client: AsyncClient, email: str, password: str) -> None:
    response = await client.post(
        '/auth/login',
        json={'email': email, 'password': password},
    )
    assert response.status_code == status.HTTP_200_OK


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