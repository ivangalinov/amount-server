from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy import and_, case, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import ColumnElement

from auth.deps import get_current_user
from category.model import Category
from database import get_db
from operation.model import Operation
from user.model import User
from workspace_access import ensure_workspace_member

router = APIRouter(prefix="/stats", tags=["stats"])


def _dialect_name(db: AsyncSession) -> str:
    bind = db.get_bind()
    return bind.dialect.name


def _utc_day_key(created_col, dialect_name: str) -> ColumnElement:
    """Строка YYYY-MM-DD в UTC (как date в клиенте по UTC)."""
    if dialect_name == "sqlite":
        return func.strftime("%Y-%m-%d", created_col)
    return func.to_char(created_col.op("AT TIME ZONE")("UTC"), "YYYY-MM-DD")


def _utc_month_key(created_col, dialect_name: str) -> ColumnElement:
    """Строка YYYY-MM в UTC."""
    if dialect_name == "sqlite":
        return func.strftime("%Y-%m", created_col)
    return func.to_char(created_col.op("AT TIME ZONE")("UTC"), "YYYY-MM")


def _operations_filter(
    workspace_id: int,
    date_from: datetime | None,
    date_to: datetime | None,
):
    conditions = [Operation.workspace_id == workspace_id]
    if date_from is not None:
        df = date_from if date_from.tzinfo else date_from.replace(tzinfo=UTC)
        conditions.append(Operation.created >= df)
    if date_to is not None:
        dt = date_to if date_to.tzinfo else date_to.replace(tzinfo=UTC)
        conditions.append(Operation.created <= dt)
    return and_(*conditions)


def _row_to_category_stat(
    cid: object,
    name: object,
    color: object,
    amount_sum: object,
) -> dict[str, object]:
    return {
        "category_id": int(cid),
        "name": str(name or "—"),
        "color": str(color or "#888"),
        "sum": int(amount_sum or 0),
    }


async def stats_balance_income_expense(
    db: AsyncSession,
    filt,
) -> tuple[int, int, int]:
    stmt = select(
        func.coalesce(func.sum(Operation.amount), 0).label("balance"),
        func.coalesce(
            func.sum(case((Operation.amount > 0, Operation.amount), else_=0)),
            0,
        ).label("total_income"),
        func.coalesce(
            func.sum(case((Operation.amount <= 0, Operation.amount), else_=0)),
            0,
        ).label("total_expense"),
    ).where(filt)
    row = (await db.execute(stmt)).one()
    return (
        int(row.balance or 0),
        int(row.total_income or 0),
        int(row.total_expense or 0),
    )


async def stats_expenses_by_category(db: AsyncSession, filt) -> list[dict[str, object]]:
    stmt = (
        select(
            Operation.category_id,
            Category.name,
            Category.color,
            func.sum(Operation.amount).label("amount_sum"),
        )
        .join(Category, Operation.category_id == Category.id)
        .where(and_(filt, Operation.amount <= 0))
        .group_by(Operation.category_id, Category.name, Category.color)
        .order_by(func.sum(Operation.amount).asc())
    )
    r = await db.execute(stmt)
    return [
        _row_to_category_stat(row["category_id"], row["name"], row["color"], row["amount_sum"])
        for row in r.mappings().all()
    ]


async def stats_income_by_category(db: AsyncSession, filt) -> list[dict[str, object]]:
    stmt = (
        select(
            Operation.category_id,
            Category.name,
            Category.color,
            func.sum(Operation.amount).label("amount_sum"),
        )
        .join(Category, Operation.category_id == Category.id)
        .where(and_(filt, Operation.amount > 0))
        .group_by(Operation.category_id, Category.name, Category.color)
        .order_by(func.sum(Operation.amount).desc())
    )
    r = await db.execute(stmt)
    return [
        _row_to_category_stat(row["category_id"], row["name"], row["color"], row["amount_sum"])
        for row in r.mappings().all()
    ]


async def stats_expenses_by_day(
    db: AsyncSession,
    filt,
    dialect_name: str,
) -> list[dict[str, object]]:
    day_key = _utc_day_key(Operation.created, dialect_name)
    stmt = (
        select(day_key.label("day"), func.sum(Operation.amount).label("amount_sum"))
        .select_from(Operation)
        .where(and_(filt, Operation.amount <= 0))
        .group_by(day_key)
        .order_by(day_key)
    )
    r = await db.execute(stmt)
    return [
        {"day": str(row["day"] or ""), "sum": int(row["amount_sum"] or 0)}
        for row in r.mappings().all()
    ]


async def stats_expenses_by_month(
    db: AsyncSession,
    filt,
    dialect_name: str,
) -> list[dict[str, object]]:
    month_key = _utc_month_key(Operation.created, dialect_name)
    stmt = (
        select(month_key.label("month"), func.sum(Operation.amount).label("amount_sum"))
        .select_from(Operation)
        .where(and_(filt, Operation.amount <= 0))
        .group_by(month_key)
        .order_by(month_key)
    )
    r = await db.execute(stmt)
    return [
        {"month": str(row["month"] or ""), "sum": int(row["amount_sum"] or 0)}
        for row in r.mappings().all()
    ]


@router.get("/dashboard")
async def dashboard_stats(
    workspace_id: int = Query(..., description="ID рабочего пространства"),
    date_from: datetime | None = Query(None),
    date_to: datetime | None = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    await ensure_workspace_member(db, current_user, workspace_id)

    filt = _operations_filter(workspace_id, date_from, date_to)
    dialect_name = _dialect_name(db)

    balance, total_income, total_expense = await stats_balance_income_expense(db, filt)
    expenses_by_category = await stats_expenses_by_category(db, filt)
    income_by_category = await stats_income_by_category(db, filt)
    expenses_by_day = await stats_expenses_by_day(db, filt, dialect_name)
    expenses_by_month = await stats_expenses_by_month(db, filt, dialect_name)

    return {
        "balance": balance,
        "total_income": total_income,
        "total_expense": total_expense,
        "expenses_by_category": expenses_by_category,
        "income_by_category": income_by_category,
        "expenses_by_day": expenses_by_day,
        "expenses_by_month": expenses_by_month,
    }
