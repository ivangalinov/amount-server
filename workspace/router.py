from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from auth.deps import get_current_user
from database import get_db
from user.model import User
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import and_, func, select, any_
from sqlalchemy.orm import selectinload
from .model import Workspace

router = APIRouter(prefix="/workspace", tags=["workspace"])

def serialize_user(user: User) -> dict:
    return {
        'id': user.id,
        'name': user.name,
    }


@router.get('/users')
async def get_workspace_users(
    workspace_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> dict:
    query_result = await db.execute(select(Workspace).where(Workspace.id == workspace_id).options(selectinload(Workspace.users)))

    wp = query_result.scalar_one_or_none()

    users = wp.users

    if current_user.id not in [u.id for u in users]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
        )
    return {
        'items': [serialize_user(u) for u in users]
    }
