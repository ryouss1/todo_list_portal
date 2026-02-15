"""add category_id task_name time_minutes to daily_reports

Revision ID: 709a8464bb48
Revises: d58961695bbb
Create Date: 2026-02-10 19:07:04.821884

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "709a8464bb48"
down_revision: Union[str, None] = "d58961695bbb"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create task_categories table first
    op.create_table(
        "task_categories",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    # Seed default "その他" category (id=7) so existing rows can reference it
    op.execute("INSERT INTO task_categories (id, name) VALUES (7, 'その他') ON CONFLICT (id) DO NOTHING")

    # Add columns as nullable first for existing data compatibility
    op.add_column("daily_reports", sa.Column("category_id", sa.Integer(), nullable=True))
    op.add_column("daily_reports", sa.Column("task_name", sa.String(length=200), nullable=True))
    op.add_column("daily_reports", sa.Column("time_minutes", sa.Integer(), nullable=True))

    # Backfill existing rows with defaults
    op.execute("UPDATE daily_reports SET category_id = 7 WHERE category_id IS NULL")
    op.execute("UPDATE daily_reports SET task_name = '' WHERE task_name IS NULL")
    op.execute("UPDATE daily_reports SET time_minutes = 0 WHERE time_minutes IS NULL")

    # Now make columns non-nullable
    op.alter_column("daily_reports", "category_id", nullable=False)
    op.alter_column("daily_reports", "task_name", nullable=False)
    op.alter_column("daily_reports", "time_minutes", nullable=False)

    op.create_foreign_key(None, "daily_reports", "task_categories", ["category_id"], ["id"])


def downgrade() -> None:
    op.drop_constraint(None, "daily_reports", type_="foreignkey")
    op.drop_column("daily_reports", "time_minutes")
    op.drop_column("daily_reports", "task_name")
    op.drop_column("daily_reports", "category_id")
    op.drop_table("task_categories")
