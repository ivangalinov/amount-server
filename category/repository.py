import typing
from database import get_db
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy import and_, func, select
from .model import Category

class ListResult(typing.TypedDict):
    items: list[Category]
    # more: bool


class CategoryRepository:

    __db: AsyncSession

    def __init__(self, db: AsyncSession):
        self.__db = db

    async def get_by_id(self, key: int) -> Category | None:
        data_set = await self.__db.execute(select(Category).where(Category.id == key))
        return data_set.scalar_one_or_none()

    async def get_list(self, list_filter: dict[str, object]) -> ListResult:
        condictions = []
        if strict_search := list_filter.get('strict_search'):
            condictions.append(strict_search)

        filt = and_(*condictions)
        result = (await self.__db.execute(
            select(Category)
            .where(filt)
        )).scalars().all()
        return ListResult(
            items=result
        )
