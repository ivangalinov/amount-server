from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from auth.deps import get_current_user
from database import get_db
from user.model import User
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import and_, func, select, any_

router = APIRouter(prefix="/users", tags=["user"])

def serialize(user: User) -> dict:
    return {
        'id': user.id,
        'name': user.name,
    }


@router.get('users')
async def get_workspace_users(
    workspace_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> list:
    query_result = await db.execute(select(User))

    result = query_result.scalars()

    return [serialize(u) for u in result]
