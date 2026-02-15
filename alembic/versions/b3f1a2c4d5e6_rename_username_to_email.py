"""rename username to email

Revision ID: b3f1a2c4d5e6
Revises: 709a8464bb48
Create Date: 2026-02-10

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "b3f1a2c4d5e6"
down_revision = "709a8464bb48"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column("users", "username", new_column_name="email", type_=sa.String(255))


def downgrade() -> None:
    op.alter_column("users", "email", new_column_name="username", type_=sa.String(100))
