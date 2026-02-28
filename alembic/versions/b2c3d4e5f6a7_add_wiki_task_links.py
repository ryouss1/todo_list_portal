"""add wiki task links

Revision ID: b2c3d4e5f6a7
Revises: a1c2d3e4f5b6
Create Date: 2026-02-25

Creates: wiki_page_task_items, wiki_page_tasks
Depends on: wiki_pages, task_list_items, tasks
"""

import sqlalchemy as sa
from alembic import op

revision = "b2c3d4e5f6a7"
down_revision = "a1c2d3e4f5b6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── wiki_page_task_items（永続紐づけ: wiki_pages ↔ task_list_items）──────
    op.create_table(
        "wiki_page_task_items",
        sa.Column("page_id", sa.Integer(), nullable=False),
        sa.Column("task_item_id", sa.Integer(), nullable=False),
        sa.Column("linked_by", sa.Integer(), nullable=True),
        sa.Column("linked_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.ForeignKeyConstraint(["page_id"], ["wiki_pages.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["task_item_id"], ["task_list_items.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["linked_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("page_id", "task_item_id"),
    )
    op.create_index("ix_wiki_page_task_items_page_id", "wiki_page_task_items", ["page_id"])
    op.create_index("ix_wiki_page_task_items_task_item_id", "wiki_page_task_items", ["task_item_id"])

    # ── wiki_page_tasks（補助紐づけ: wiki_pages ↔ tasks、SET NULL対応）────────
    op.create_table(
        "wiki_page_tasks",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("page_id", sa.Integer(), nullable=False),
        sa.Column("task_id", sa.Integer(), nullable=True),
        sa.Column("task_title", sa.String(500), nullable=False),
        sa.Column("linked_by", sa.Integer(), nullable=True),
        sa.Column("linked_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.ForeignKeyConstraint(["page_id"], ["wiki_pages.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["task_id"], ["tasks.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["linked_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_wiki_page_tasks_page_id", "wiki_page_tasks", ["page_id"])
    op.create_index("ix_wiki_page_tasks_task_id", "wiki_page_tasks", ["task_id"])
    # Partial unique index: (page_id, task_id) WHERE task_id IS NOT NULL
    op.execute(
        "CREATE UNIQUE INDEX ix_wiki_page_tasks_unique "
        "ON wiki_page_tasks (page_id, task_id) WHERE task_id IS NOT NULL"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_wiki_page_tasks_unique")
    op.drop_index("ix_wiki_page_tasks_task_id", table_name="wiki_page_tasks")
    op.drop_index("ix_wiki_page_tasks_page_id", table_name="wiki_page_tasks")
    op.drop_table("wiki_page_tasks")
    op.drop_index("ix_wiki_page_task_items_task_item_id", table_name="wiki_page_task_items")
    op.drop_index("ix_wiki_page_task_items_page_id", table_name="wiki_page_task_items")
    op.drop_table("wiki_page_task_items")
