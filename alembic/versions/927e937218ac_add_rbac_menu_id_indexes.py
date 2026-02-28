"""add_rbac_menu_id_indexes

Revision ID: 927e937218ac
Revises: 08089f89ae62
Create Date: 2026-02-28

"""

from alembic import op

# revision identifiers
revision = "927e937218ac"
down_revision = "08089f89ae62"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index("ix_role_menus_menu_id", "role_menus", ["menu_id"])
    op.create_index("ix_user_menus_menu_id", "user_menus", ["menu_id"])


def downgrade() -> None:
    op.drop_index("ix_user_menus_menu_id", table_name="user_menus")
    op.drop_index("ix_role_menus_menu_id", table_name="role_menus")
