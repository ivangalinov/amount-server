from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from database import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from .model import Category, CategoryType

router = APIRouter(
    prefix='/category',
    tags=['Category']
)


class CategoryCreate(BaseModel):
    name: str = Field(..., min_length=1)
    workspace_id: int
    type: CategoryType
    color: str = Field(..., min_length=1)
    limit: str | None = None
    user_id: int | None = None


class CategoryUpdate(BaseModel):
    name: str | None = Field(None, min_length=1)
    workspace_id: int | None = None
    type: CategoryType | None = None
    color: str | None = Field(None, min_length=1)
    limit: str | None = None
    user_id: int | None = None


def serialize_batch(items: list[Category]) -> list[dict]:
    return [
        serialize(item) for item in items
    ]

def serialize(item: Category) -> dict:
    return {
        'id': item.id,
        'name': item.name,
        'type': item.type,
        'color': item.color,
        'limit': item.limit,
        # 'user_id': item.user_id
    }


@router.post('/', status_code=status.HTTP_201_CREATED)
async def create_category(body: CategoryCreate, db: AsyncSession = Depends(get_db)):
    category = Category(
        name=body.name,
        workspace_id=body.workspace_id,
        type=body.type,
        color=body.color,
        limit=body.limit,
        user_id=body.user_id,
    )
    db.add(category)
    await db.commit()
    await db.refresh(category)
    return serialize(category)


@router.patch('/{category_id}')
async def update_category(
    category_id: int,
    body: CategoryUpdate,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Category).where(Category.id == category_id))
    category = result.scalar_one_or_none()
    if category is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Category not found')

    for key, value in body.model_dump(exclude_unset=True).items():
        setattr(category, key, value)

    await db.commit()
    await db.refresh(category)
    return serialize(category)


@router.get('/')
async def get_categories(
    category_type: CategoryType | None = Query(None, alias='type'),
    db: AsyncSession = Depends(get_db),
):
    query = select(Category)
    if category_type is not None:
        query = query.where(Category.type == category_type)
    query_result = await db.execute(query)
    result = query_result.scalars().all()
    return {
        'items': serialize_batch(result),
        'total': 10
    }
