"""add category_id to tasks

Revision ID: d5e6f7a8b9c0
Revises: c4d5e6f7a8b9
Create Date: 2026-02-10

"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "d5e6f7a8b9c0"
down_revision = "c4d5e6f7a8b9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("tasks", sa.Column("category_id", sa.Integer(), sa.ForeignKey("task_categories.id"), nullable=True))


def downgrade() -> None:
    op.drop_column("tasks", "category_id")
