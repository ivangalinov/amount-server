from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from auth.deps import get_current_user
from category.model import Category
from database import get_db
from operation.model import Operation
from user.model import User
from workspace_access import ensure_workspace_member, user_workspace_ids

router = APIRouter(prefix="/operation", tags=["operation"])


class OperationCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    workspace_id: int
    category_id: int
    title: str = Field(..., min_length=1, max_length=512)
    amount: int
    created: datetime | None = None

    @field_validator("amount", mode="before")
    @classmethod
    def amount_to_int(cls, v: object) -> int:
        if isinstance(v, bool):
            raise ValueError("invalid amount")
        return int(round(float(v)))  # type: ignore[arg-type]


class OperationUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    category_id: int | None = None
    title: str | None = Field(None, min_length=1, max_length=512)
    amount: int | None = None
    created: datetime | None = None

    @field_validator("amount", mode="before")
    @classmethod
    def amount_to_int(cls, v: object) -> int | None:
        if v is None:
            return None
        if isinstance(v, bool):
            raise ValueError("invalid amount")
        return int(round(float(v)))  # type: ignore[arg-type]


def serialize(op: Operation) -> dict:
    return {
        "id": op.id,
        "amount": op.amount,
        "category_id": op.category_id,
        "title": op.title,
        "user_id": op.user_id,
        "workspace_id": op.workspace_id,
        "created": op.created.isoformat(),
    }


async def _get_operation_for_user(
    db: AsyncSession,
    user: User,
    operation_id: int,
) -> Operation:
    r = await db.execute(select(Operation).where(Operation.id == operation_id))
    op = r.scalar_one_or_none()
    if op is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Operation not found",
        )
    allowed = await user_workspace_ids(db, user.id)
    if op.workspace_id not in allowed:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Operation not found",
        )
    return op


async def _category_belongs_to_workspace(
    db: AsyncSession,
    category_id: int,
    workspace_id: int,
) -> Category:
    r = await db.execute(select(Category).where(Category.id == category_id))
    cat = r.scalar_one_or_none()
    if cat is None or cat.workspace_id != workspace_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found",
        )
    return cat


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_operation(
    body: OperationCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    await ensure_workspace_member(db, current_user, body.workspace_id)
    await _category_belongs_to_workspace(db, body.category_id, body.workspace_id)
    created_at = body.created
    if created_at is not None and created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=UTC)
    if created_at is None:
        created_at = datetime.now(UTC)
    op = Operation(
        workspace_id=body.workspace_id,
        category_id=body.category_id,
        title=body.title,
        amount=body.amount,
        user_id=current_user.id,
        created=created_at,
    )
    db.add(op)
    await db.commit()
    await db.refresh(op)
    return serialize(op)


@router.get("")
async def list_operations(
    workspace_id: int = Query(..., description="ID рабочего пространства"),
    category_id: int | None = Query(None),
    user_id: int | None = Query(None),
    date_from: datetime | None = Query(None),
    date_to: datetime | None = Query(None),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    await ensure_workspace_member(db, current_user, workspace_id)

    conditions = [Operation.workspace_id == workspace_id]
    if category_id is not None:
        conditions.append(Operation.category_id == category_id)
    if user_id is not None:
        conditions.append(Operation.user_id == user_id)
    if date_from is not None:
        df = date_from if date_from.tzinfo else date_from.replace(tzinfo=UTC)
        conditions.append(Operation.created >= df)
    if date_to is not None:
        dt = date_to if date_to.tzinfo else date_to.replace(tzinfo=UTC)
        conditions.append(Operation.created <= dt)

    filt = and_(*conditions)

    count_r = await db.execute(
        select(func.count()).select_from(Operation).where(filt)
    )
    total = int(count_r.scalar_one())

    list_r = await db.execute(
        select(Operation)
        .where(filt)
        .order_by(Operation.created.desc())
        .offset(offset)
        .limit(limit)
    )
    rows = list_r.scalars().all()
    return {"items": [serialize(o) for o in rows], "total": total}


@router.get("/{operation_id}")
async def get_operation(
    operation_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    op = await _get_operation_for_user(db, current_user, operation_id)
    return serialize(op)


@router.patch("/{operation_id}")
async def update_operation(
    operation_id: int,
    body: OperationUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    op = await _get_operation_for_user(db, current_user, operation_id)
    data = body.model_dump(exclude_unset=True)
    if "category_id" in data and data["category_id"] is not None:
        await _category_belongs_to_workspace(
            db,
            data["category_id"],
            op.workspace_id,
        )
    if "created" in data and data["created"] is not None:
        c = data["created"]
        if c.tzinfo is None:
            data["created"] = c.replace(tzinfo=UTC)
    for key, value in data.items():
        setattr(op, key, value)
    await db.commit()
    await db.refresh(op)
    return serialize(op)


@router.delete("/{operation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_operation(
    operation_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    op = await _get_operation_for_user(db, current_user, operation_id)
    await db.delete(op)
    await db.commit()
