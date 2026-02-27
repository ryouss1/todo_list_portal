"""Migrate groups to departments, update log_sources FK

Revision ID: b7c8d9e0f1a2
Revises: a9b8c7d6e5f4
Create Date: 2026-02-28 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b7c8d9e0f1a2"
down_revision: Union[str, None] = "a9b8c7d6e5f4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()

    # 1. Drop the old FK constraint on log_sources.group_id → groups.id first,
    #    so subsequent UPDATE can freely change group_id values without FK checks.
    op.drop_constraint("fk_log_sources_group_id", "log_sources", type_="foreignkey")

    # 2. Rename log_sources.group_id → log_sources.department_id
    op.alter_column("log_sources", "group_id", new_column_name="department_id")

    # 3. Copy groups → departments (as root-level departments).
    #    ON CONFLICT (name) DO NOTHING handles duplicate names.
    conn.execute(
        sa.text(
            """
            INSERT INTO departments (name, description, sort_order, is_active, created_at, updated_at)
            SELECT name, description, sort_order, true, NOW(), NOW()
            FROM groups
            ON CONFLICT (name) DO NOTHING
            """
        )
    )

    # 4. Update log_sources.department_id to point to the new department id.
    #    Match the old group by name to find the corresponding department id.
    conn.execute(
        sa.text(
            """
            UPDATE log_sources ls
            SET department_id = d.id
            FROM groups g
            JOIN departments d ON d.name = g.name
            WHERE ls.department_id = g.id
            """
        )
    )

    # 5. Add new FK constraint log_sources.department_id → departments.id
    op.create_foreign_key(
        "fk_log_sources_department_id",
        "log_sources",
        "departments",
        ["department_id"],
        ["id"],
    )

    # 6. Drop the groups table (no more FK references from any table)
    op.drop_table("groups")


def downgrade() -> None:
    conn = op.get_bind()

    # 1. Recreate the groups table (empty — data migration is one-way, cannot restore original groups)
    op.create_table(
        "groups",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("description", sa.String(length=500), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )

    # 2. Drop FK constraint log_sources → departments
    op.drop_constraint("fk_log_sources_department_id", "log_sources", type_="foreignkey")

    # 3. NULL out log_sources.department_id before renaming back to group_id.
    #    The restored groups table is empty, so existing department_id values cannot
    #    satisfy FK integrity to groups. Data is intentionally lost on downgrade.
    conn.execute(sa.text("UPDATE log_sources SET department_id = NULL"))

    # 4. Rename log_sources.department_id → log_sources.group_id
    op.alter_column("log_sources", "department_id", new_column_name="group_id")

    # 5. Re-add FK constraint log_sources → groups
    op.create_foreign_key(
        "fk_log_sources_group_id",
        "log_sources",
        "groups",
        ["group_id"],
        ["id"],
    )
