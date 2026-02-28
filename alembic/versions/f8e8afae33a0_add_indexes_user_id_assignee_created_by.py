"""add_indexes_user_id_assignee_created_by

Revision ID: f8e8afae33a0
Revises: d4e5f6a7b8c9
Create Date: 2026-02-25 18:11:26.905679

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "f8e8afae33a0"
down_revision: Union[str, None] = "d4e5f6a7b8c9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index(op.f("ix_daily_reports_user_id"), "daily_reports", ["user_id"], unique=False)
    op.create_index(op.f("ix_presence_logs_user_id"), "presence_logs", ["user_id"], unique=False)
    op.create_index(op.f("ix_task_list_items_assignee_id"), "task_list_items", ["assignee_id"], unique=False)
    op.create_index(op.f("ix_task_list_items_created_by"), "task_list_items", ["created_by"], unique=False)
    op.create_index(op.f("ix_tasks_user_id"), "tasks", ["user_id"], unique=False)
    op.create_index(op.f("ix_todos_user_id"), "todos", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_todos_user_id"), table_name="todos")
    op.drop_index(op.f("ix_tasks_user_id"), table_name="tasks")
    op.drop_index(op.f("ix_task_list_items_created_by"), table_name="task_list_items")
    op.drop_index(op.f("ix_task_list_items_assignee_id"), table_name="task_list_items")
    op.drop_index(op.f("ix_presence_logs_user_id"), table_name="presence_logs")
    op.drop_index(op.f("ix_daily_reports_user_id"), table_name="daily_reports")
