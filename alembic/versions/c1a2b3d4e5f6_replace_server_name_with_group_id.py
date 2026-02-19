"""replace server_name with group_id

Revision ID: c1a2b3d4e5f6
Revises: 0d0894c74444
Create Date: 2026-02-18 12:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "c1a2b3d4e5f6"
down_revision = "0d0894c74444"
branch_labels = None
depends_on = None


def upgrade():
    # 1. Add group_id column (nullable initially)
    op.add_column("log_sources", sa.Column("group_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_log_sources_group_id", "log_sources", "groups", ["group_id"], ["id"]
    )

    # 2. Migrate existing data: set group_id to default group (id=1)
    op.execute("UPDATE log_sources SET group_id = 1")

    # 3. Make group_id NOT NULL
    op.alter_column("log_sources", "group_id", nullable=False)

    # 4. Drop server_name column
    op.drop_column("log_sources", "server_name")


def downgrade():
    # 1. Re-add server_name column (nullable initially)
    op.add_column(
        "log_sources", sa.Column("server_name", sa.String(200), nullable=True)
    )

    # 2. Populate server_name with placeholder
    op.execute("UPDATE log_sources SET server_name = 'unknown'")

    # 3. Make server_name NOT NULL
    op.alter_column("log_sources", "server_name", nullable=False)

    # 4. Drop group_id FK and column
    op.drop_constraint("fk_log_sources_group_id", "log_sources", type_="foreignkey")
    op.drop_column("log_sources", "group_id")
