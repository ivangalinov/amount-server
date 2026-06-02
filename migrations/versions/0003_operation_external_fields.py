from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic (max 32 chars in alembic_version.version_num).
revision: str = "0003_operation_external_fields"
down_revision: str | None = "0002_user_email_password"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("operations", sa.Column("ext_key", sa.String(), nullable=True))
    op.add_column("operations", sa.Column("ext_source", sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column("operations", "ext_source")
    op.drop_column("operations", "ext_key")
