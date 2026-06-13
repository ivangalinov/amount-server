from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, EmailStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from auth.deps import get_current_user
from user.model import User
from .model import WorkspaceUser, Workspace

router = APIRouter(prefix="/workspace", tags=["workspace"])


class WorkspaceMemberAdd(BaseModel):
    workspace_id: int
    email: EmailStr


async def parse_workspace_member_add(request: Request) -> WorkspaceMemberAdd:
    content_type = request.headers.get('content-type', '')
    if content_type.startswith('application/json'):
        return WorkspaceMemberAdd.model_validate(await request.json())

    if (
        content_type.startswith('multipart/form-data')
        or content_type.startswith('application/x-www-form-urlencoded')
    ):
        form = await request.form()
        try:
            return WorkspaceMemberAdd(
                workspace_id=int(form['workspace_id']),
                email=form['email'],
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail='workspace_id and email are required',
            ) from exc

    raise HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail='Expected JSON or form data with workspace_id and email',
    )


async def add_workspace_member_impl(
    db: AsyncSession,
    workspace_id: int,
    email: str,
) -> dict:
    workspace = (await db.execute(
        select(Workspace).where(Workspace.id == workspace_id)
    )).scalar_one_or_none()
    if workspace is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Workspace not found')

    user = (await db.execute(
        select(User).where(User.email == email)
    )).scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='User not found')

    existing = (await db.execute(
        select(WorkspaceUser.id).where(
            WorkspaceUser.user_id == user.id,
            WorkspaceUser.workspace_id == workspace_id,
        ).limit(1)
    )).scalar_one_or_none()
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail='User is already a member of this workspace',
        )

    membership = WorkspaceUser(user_id=user.id, workspace_id=workspace_id)
    db.add(membership)
    await db.commit()
    await db.refresh(membership)

    return {
        'id': membership.id,
        'workspace_id': membership.workspace_id,
        'user_id': user.id,
        'email': user.email,
        'name': user.name,
    }


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
    workspace = (await db.execute(
        select(Workspace)
        .join(WorkspaceUser, WorkspaceUser.workspace_id == Workspace.id)
        .where(WorkspaceUser.user_id == current_user.id)
        .order_by(WorkspaceUser.id.desc())
        .limit(1)
    )).scalar_one_or_none()

    if workspace is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Workspace not found',
        )

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

    query = (
        select(User)
        .join(WorkspaceUser, WorkspaceUser.user_id == User.id)
        .where(WorkspaceUser.workspace_id == workspace_id)
    )

    users = list((await db.execute(query)).scalars())


    if current_user.id not in map(lambda u: u.id, users):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
        )    

    return {
        'items': [serialize_user(u) for u in users]
    }


@router.post('/members', status_code=status.HTTP_201_CREATED)
async def add_workspace_member(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> dict:
    body = await parse_workspace_member_add(request)
    return await add_workspace_member_impl(db, body.workspace_id, str(body.email))
