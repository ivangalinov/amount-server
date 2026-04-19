from database import get_db
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy import and_, func, select
from .model import Category

class OperationReposotory:

    __db: AsyncSession

    def __init__(self, db: AsyncSession):
        self.__db = db

    async def get_by_id(self, key: int):
        data_set = await self.__db.execute(select(Category).where(Category.id == key))
        return data_set.scalar_one_or_none()
