"""Привести category_type к нижнему регистру (income/expense/transfer)."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0004_category_type_lowercase"
down_revision: str | None = "0003_operation_external_fields"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_RENAMES = (
    ("INCOME", "income"),
    ("EXPENSE", "expense"),
    ("TRANSFER", "transfer"),
)


def _enum_labels(bind: sa.engine.Connection) -> set[str]:
    rows = bind.execute(
        sa.text(
            """
            SELECT e.enumlabel
            FROM pg_enum e
            JOIN pg_type t ON e.enumtypid = t.oid
            WHERE t.typname = 'category_type'
            """
        )
    ).scalars()
    return set(rows)


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    labels = _enum_labels(bind)
    for old, new in _RENAMES:
        if old in labels and new not in labels:
            op.execute(sa.text(f"ALTER TYPE category_type RENAME VALUE '{old}' TO '{new}'"))


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    labels = _enum_labels(bind)
    for old, new in reversed(_RENAMES):
        if new in labels and old not in labels:
            op.execute(sa.text(f"ALTER TYPE category_type RENAME VALUE '{new}' TO '{old}'"))
