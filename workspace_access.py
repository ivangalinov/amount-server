"""Проверки членства пользователя в workspace (общие для роутеров)."""

from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from user.model import User
from workspace.model import WorkspaceUser


async def user_workspace_ids(db: AsyncSession, user_id: int) -> set[int]:
    r = await db.execute(
        select(WorkspaceUser.workspace_id).where(WorkspaceUser.user_id == user_id)
    )
    return set(r.scalars().all())


async def ensure_workspace_member(
    db: AsyncSession,
    user: User,
    workspace_id: int,
) -> None:
    if workspace_id not in await user_workspace_ids(db, user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not a member of this workspace",
        )
