"""add attendance_breaks table

Revision ID: a1b2c3d4e5f6
Revises: fa32f8e03649
Create Date: 2026-02-10 20:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, None] = "fa32f8e03649"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create attendance_breaks table
    op.create_table(
        "attendance_breaks",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("attendance_id", sa.Integer(), nullable=False),
        sa.Column("break_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("break_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.ForeignKeyConstraint(["attendance_id"], ["attendances.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    # 2. Migrate existing break data from attendances to attendance_breaks
    op.execute(
        """
        INSERT INTO attendance_breaks (attendance_id, break_start, break_end)
        SELECT id, break_start, break_end
        FROM attendances
        WHERE break_start IS NOT NULL
        """
    )

    # 3. Drop old break columns from attendances
    op.drop_column("attendances", "break_start")
    op.drop_column("attendances", "break_end")


def downgrade() -> None:
    # 1. Re-add break columns to attendances
    op.add_column("attendances", sa.Column("break_end", sa.DateTime(timezone=True), nullable=True))
    op.add_column("attendances", sa.Column("break_start", sa.DateTime(timezone=True), nullable=True))

    # 2. Migrate first break back to attendances
    op.execute(
        """
        UPDATE attendances SET break_start = ab.break_start, break_end = ab.break_end
        FROM (
            SELECT DISTINCT ON (attendance_id) attendance_id, break_start, break_end
            FROM attendance_breaks
            ORDER BY attendance_id, id
        ) ab
        WHERE attendances.id = ab.attendance_id
        """
    )

    # 3. Drop attendance_breaks table
    op.drop_table("attendance_breaks")
