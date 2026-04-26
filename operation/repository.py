import typing
from datetime import UTC
from sqlalchemy.ext.asyncio import AsyncSession
from category import Category, CategoryType
from sqlalchemy import and_, select
from .model import Operation


from datetime import UTC
from sqlalchemy.orm import joinedload

from operation.model import Operation
from user.model import User


class ListFilter(typing.TypedDict):
    workspace_id: int | None
    category_id: int | None
    user_id: int | None
    date_from: str | None
    date_to: str | None
    type: CategoryType | None

class Navigation(typing.TypedDict):
    limit: int
    page: int

class ListResult(typing.TypedDict):
    items: list[Operation]
    more: bool


class OperationReposotory:

    __db: AsyncSession

    def __init__(self, db: AsyncSession):
        self.__db = db

    async def get_by_id(self, key: int) -> Operation | None:
        data_set = await self.__db.execute(select(Operation).where(Operation.id == key))
        return data_set.scalar_one_or_none()


    async def get_list(self, list_filter: ListFilter, navigation: Navigation) -> ListResult:
        conditions = []
        if workspace_id := list_filter['workspace_id']:
            conditions.append(Operation.workspace_id == workspace_id)
        if category_id := list_filter['category_id']:
            conditions.append(Operation.category_id == category_id)
        if user_id := list_filter['user_id']:
            conditions.append(Operation.user_id == user_id)
        if date_from := list_filter['date_from']:
            df = date_from if date_from.tzinfo else date_from.replace(tzinfo=UTC)
            conditions.append(Operation.created >= df)
        if date_to := list_filter['date_to']:
            dt = date_to if date_to.tzinfo else date_to.replace(tzinfo=UTC)
            conditions.append(Operation.created <= dt)

        if type_ := list_filter['type']:
            match type_:
                case CategoryType.INCOME:
                    conditions.append(Operation.amount > 0)
                case CategoryType.EXPENSE:
                    conditions.append(Operation.amount < 0)

        filt = and_(*conditions)

        limit = navigation['limit']
        offset = navigation['page'] * limit

        list_result = await self.__db.execute(
            select(Operation)
            .where(filt)
            .order_by(Operation.created.desc())
            .offset(offset)
            .limit(limit + 1)
            .options(
                joinedload(
                    Operation.user
                ).load_only(
                    User.name
                )
            ).options(
                joinedload(
                    Operation.category
                ).load_only(
                    Category.name,
                    Category.color
                )
            )
        )
        
        rows = list_result.scalars().all()

        has_more = len(rows) > limit
        return dict(
            items=rows[:limit],
            more=has_more,
        )
