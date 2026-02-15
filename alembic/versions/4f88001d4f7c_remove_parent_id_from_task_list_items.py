"""remove parent_id from task_list_items

Revision ID: 4f88001d4f7c
Revises: 72671cad997f
Create Date: 2026-02-11 09:31:00.259835

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4f88001d4f7c'
down_revision: Union[str, None] = '72671cad997f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_constraint('task_list_items_parent_id_fkey', 'task_list_items', type_='foreignkey')
    op.drop_column('task_list_items', 'parent_id')


def downgrade() -> None:
    op.add_column('task_list_items', sa.Column('parent_id', sa.INTEGER(), autoincrement=False, nullable=True))
    op.create_foreign_key('task_list_items_parent_id_fkey', 'task_list_items', 'task_list_items', ['parent_id'], ['id'], ondelete='CASCADE')
