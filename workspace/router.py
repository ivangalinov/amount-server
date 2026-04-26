from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from auth.deps import get_current_user
from user.model import User
from .model import WorkspaceUser, Workspace

router = APIRouter(prefix="/workspace", tags=["workspace"])

def serialize_user(user: User) -> dict:
    return {
        'id': user.id,
        'name': user.name,
    }

@router.get('/active')
async def get_active_workspace(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> dict:
    subquery = select(WorkspaceUser.workspace_id).where(WorkspaceUser.user_id == current_user.id)
    workspace = (await db.execute(select(Workspace).where(
        Workspace.id == subquery
    ))).scalar_one()

    return {
        'id': workspace.id,
        'name': workspace.name,
    }


@router.get('/users')
async def get_workspace_users(
    workspace_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> dict:

    relation_subquery = select(WorkspaceUser.user_id).where(
        WorkspaceUser.workspace_id == workspace_id
    ).subquery()

    query = select(User).where(
        User.id == relation_subquery
    )

    users = list((await db.execute(query)).scalars())


    if current_user.id not in map(lambda u: u.id, users):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
        )    

    return {
        'items': [serialize_user(u) for u in users]
    }
