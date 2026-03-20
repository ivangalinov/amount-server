from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic (max 32 chars in alembic_version.version_num).
revision: str = "0001_default_now_created"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column(
        "operations",
        "created",
        existing_type=sa.DateTime(timezone=True),
        server_default=sa.text("NOW()"),
        existing_nullable=False,
    )


def downgrade() -> None:
    op.alter_column(
        "operations",
        "created",
        existing_type=sa.DateTime(timezone=True),
        server_default=None,
        existing_nullable=False,
    )

