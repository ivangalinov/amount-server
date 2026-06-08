"""Привести PostgreSQL enum category_type к нижнему регистру (income/expense/transfer).

Запуск из каталога amount-server:
    python scripts/fix_category_type_enum.py
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

from sqlalchemy import text

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from database import engine  # noqa: E402

_RENAMES = (
    ("INCOME", "income"),
    ("EXPENSE", "expense"),
    ("TRANSFER", "transfer"),
)


async def main() -> None:
    async with engine.begin() as conn:
        dialect = conn.dialect.name
        if dialect != "postgresql":
            print(f"Skip: dialect is {dialect}, not postgresql")
            return

        labels = set(
            (
                await conn.execute(
                    text(
                        """
                        SELECT e.enumlabel
                        FROM pg_enum e
                        JOIN pg_type t ON e.enumtypid = t.oid
                        WHERE t.typname = 'category_type'
                        """
                    )
                )
            ).scalars()
        )
        print("Before:", sorted(labels))

        for old, new in _RENAMES:
            if old in labels and new not in labels:
                await conn.execute(
                    text(f"ALTER TYPE category_type RENAME VALUE '{old}' TO '{new}'")
                )

        labels = set(
            (
                await conn.execute(
                    text(
                        """
                        SELECT e.enumlabel
                        FROM pg_enum e
                        JOIN pg_type t ON e.enumtypid = t.oid
                        WHERE t.typname = 'category_type'
                        """
                    )
                )
            ).scalars()
        )
        print("After:", sorted(labels))


if __name__ == "__main__":
    asyncio.run(main())
