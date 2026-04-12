from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic (max 32 chars in alembic_version.version_num).
revision: str = "0002_user_email_password"
down_revision: str | None = "0001_default_now_created"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Bcrypt hash of "__m__" — only for backfilling legacy rows without a password (cannot be used to log in).
_LEGACY_PASSWORD_HASH = (
    "$2b$12$teO97NU9W8cWLO.s9ejC4uIZ6CEk7i0lqXfZtN82nO/RCCPAhk4Pa"
)


def upgrade() -> None:
    op.add_column("users", sa.Column("email", sa.String(length=255), nullable=True))
    op.add_column("users", sa.Column("password_hash", sa.String(length=255), nullable=True))

    bind = op.get_bind()
    dialect = bind.dialect.name

    if dialect == "postgresql":
        op.execute(
            sa.text(
                """
                UPDATE users SET
                  email = COALESCE(
                    NULLIF(TRIM(email), ''),
                    'legacy-' || id::text || '@amount.local'
                  ),
                  password_hash = COALESCE(password_hash, :ph)
                WHERE email IS NULL OR password_hash IS NULL OR TRIM(email) = ''
                """
            ).bindparams(ph=_LEGACY_PASSWORD_HASH)
        )
    else:
        op.execute(
            sa.text(
                """
                UPDATE users SET
                  email = COALESCE(
                    NULLIF(TRIM(email), ''),
                    'legacy-' || CAST(id AS TEXT) || '@amount.local'
                  ),
                  password_hash = COALESCE(password_hash, :ph)
                WHERE email IS NULL OR password_hash IS NULL OR TRIM(email) = ''
                """
            ).bindparams(ph=_LEGACY_PASSWORD_HASH)
        )

    op.alter_column("users", "email", existing_type=sa.String(length=255), nullable=False)
    op.alter_column(
        "users", "password_hash", existing_type=sa.String(length=255), nullable=False
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_users_email", table_name="users")
    op.drop_column("users", "password_hash")
    op.drop_column("users", "email")
