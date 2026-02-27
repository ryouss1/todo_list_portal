"""users group_id to department_id

Revision ID: a9b8c7d6e5f4
Revises: 8868b471d6cb
Down revision = '8868b471d6cb'
Branch labels: None
Depends on: None
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "a9b8c7d6e5f4"
down_revision = "8868b471d6cb"
branch_labels = None
depends_on = None


def upgrade():
    # Drop old FK constraint
    op.execute("ALTER TABLE users DROP CONSTRAINT IF EXISTS users_group_id_fkey")
    # Rename column
    op.alter_column("users", "group_id", new_column_name="department_id")
    # NULL out any department_id values that don't correspond to departments
    # (old group_id values may reference groups.id which is not the same as departments.id)
    op.execute("UPDATE users SET department_id = NULL WHERE department_id IS NOT NULL")
    # Add new FK constraint
    op.create_foreign_key(
        "users_department_id_fkey",
        "users",
        "departments",
        ["department_id"],
        ["id"],
        ondelete="SET NULL",
    )
    # Drop old index, create new one
    op.execute("DROP INDEX IF EXISTS ix_users_group_id")
    op.create_index("ix_users_department_id", "users", ["department_id"])


def downgrade():
    op.drop_constraint("users_department_id_fkey", "users", type_="foreignkey")
    op.alter_column("users", "department_id", new_column_name="group_id")
    op.create_foreign_key(
        "users_group_id_fkey",
        "users",
        "groups",
        ["group_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.execute("DROP INDEX IF EXISTS ix_users_department_id")
    op.create_index("ix_users_group_id", "users", ["group_id"])
