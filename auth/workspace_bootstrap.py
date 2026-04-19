from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from user.model import User
from workspace.model import Workspace, WorkspaceUser

_WORKSPACE_NAME_MAX = 255


def default_workspace_name(user_name: str) -> str:
    base = (user_name or "").strip() or "Workspace"
    label = f"{base} — workspace"
    return label[:_WORKSPACE_NAME_MAX]


async def ensure_user_has_default_workspace(db: AsyncSession, user: User) -> None:
    """If the user has no workspace membership, create one workspace and link them."""
    r = await db.execute(
        select(WorkspaceUser.id).where(WorkspaceUser.user_id == user.id).limit(1)
    )
    if r.scalar_one_or_none() is not None:
        return
    ws = Workspace(name=default_workspace_name(user.name))
    db.add(ws)
    await db.flush()
    db.add(WorkspaceUser(user_id=user.id, workspace_id=ws.id))
