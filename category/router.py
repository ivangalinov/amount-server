from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from auth.deps import get_current_user
from database import get_db
from user.model import User
from workspace.model import WorkspaceUser

from .model import Category, CategoryType

router = APIRouter(
    prefix="/category",
    tags=["Category"],
)


class CategoryCreate(BaseModel):
    name: str = Field(..., min_length=1)
    workspace_id: int
    type: CategoryType
    color: str = Field(..., min_length=1)
    limit: str | None = None


class CategoryUpdate(BaseModel):
    name: str | None = Field(None, min_length=1)
    workspace_id: int | None = None
    type: CategoryType | None = None
    color: str | None = Field(None, min_length=1)
    limit: str | None = None


class CategoryGet(BaseModel):
    id: int
    name: str
    type: CategoryType
    color: str
    limit: str | None = None
    workspace_id: int


async def _user_workspace_ids(db: AsyncSession, user_id: int) -> set[int]:
    r = await db.execute(
        select(WorkspaceUser.workspace_id).where(WorkspaceUser.user_id == user_id)
    )
    return set(r.scalars().all())


async def _ensure_workspace_member(
    db: AsyncSession,
    user: User,
    workspace_id: int,
) -> None:
    if workspace_id not in await _user_workspace_ids(db, user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not a member of this workspace",
        )


async def _get_category_for_user(
    db: AsyncSession,
    user: User,
    category_id: int,
) -> Category:
    r = await db.execute(select(Category).where(Category.id == category_id))
    category = r.scalar_one_or_none()
    if category is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found",
        )
    allowed = await _user_workspace_ids(db, user.id)
    if category.workspace_id not in allowed:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found",
        )
    return category


def serialize_batch(items: list[Category]) -> list[dict]:
    return [serialize(item) for item in items]


def serialize(item: Category) -> dict:
    return {
        "id": item.id,
        "name": item.name,
        "type": item.type,
        "color": item.color,
        "limit": item.limit,
        "workspace_id": item.workspace_id,
    }


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_category(
    body: CategoryCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    await _ensure_workspace_member(db, current_user, body.workspace_id)
    category = Category(
        name=body.name,
        workspace_id=body.workspace_id,
        type=body.type,
        color=body.color,
        limit=body.limit,
        user_id=current_user.id,
    )
    db.add(category)
    await db.commit()
    await db.refresh(category)
    return serialize(category)


@router.patch("/{category_id}")
async def update_category(
    category_id: int,
    body: CategoryUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    category = await _get_category_for_user(db, current_user, category_id)
    data = body.model_dump(exclude_unset=True)
    if "workspace_id" in data:
        new_ws = data["workspace_id"]
        if new_ws is not None:
            await _ensure_workspace_member(db, current_user, new_ws)
    for key, value in data.items():
        setattr(category, key, value)
    await db.commit()
    await db.refresh(category)
    return serialize(category)


@router.delete("/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_category(
    category_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    category = await _get_category_for_user(db, current_user, category_id)
    await db.delete(category)
    await db.commit()


@router.get("")
async def get_categories(
    category_type: CategoryType | None = Query(None, alias="type"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    allowed = await _user_workspace_ids(db, current_user.id)
    if not allowed:
        return {"items": [], "total": 0}
    query = select(Category).where(Category.workspace_id.in_(allowed))
    if category_type is not None:
        query = query.where(Category.type == category_type)
    query_result = await db.execute(query)
    result = query_result.scalars().all()
    items = serialize_batch(list(result))
    return {"items": items, "total": len(items)}


@router.get("/{category_id}", response_model=CategoryGet)
async def get_category(
    category_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    category = await _get_category_for_user(db, current_user, category_id)
    return serialize(category)
