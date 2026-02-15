"""add backlog_ticket_id to tasks

Revision ID: c4d5e6f7a8b9
Revises: b3f1a2c4d5e6
Create Date: 2026-02-10

"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "c4d5e6f7a8b9"
down_revision = "b3f1a2c4d5e6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("tasks", sa.Column("backlog_ticket_id", sa.String(50), nullable=True))


def downgrade() -> None:
    op.drop_column("tasks", "backlog_ticket_id")
