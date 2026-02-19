"""add_log_source_paths

Revision ID: b8f2a1c3d4e5
Revises: 3c7419e092cb
Create Date: 2026-02-18 12:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b8f2a1c3d4e5"
down_revision: Union[str, None] = "3c7419e092cb"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create log_source_paths table
    op.create_table(
        "log_source_paths",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("source_id", sa.Integer(), nullable=False),
        sa.Column("base_path", sa.String(length=1000), nullable=False),
        sa.Column("file_pattern", sa.String(length=200), server_default="*.log", nullable=False),
        sa.Column("is_enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.ForeignKeyConstraint(["source_id"], ["log_sources.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_log_source_paths_source_id"), "log_source_paths", ["source_id"], unique=False)

    # 2. Migrate existing base_path/file_pattern from log_sources to log_source_paths
    conn = op.get_bind()
    sources = conn.execute(
        sa.text("SELECT id, base_path, file_pattern FROM log_sources")
    ).fetchall()
    for source in sources:
        conn.execute(
            sa.text(
                "INSERT INTO log_source_paths (source_id, base_path, file_pattern, is_enabled) "
                "VALUES (:source_id, :base_path, :file_pattern, true)"
            ),
            {"source_id": source[0], "base_path": source[1], "file_pattern": source[2]},
        )

    # 3. Add path_id column to log_files (nullable initially)
    op.add_column("log_files", sa.Column("path_id", sa.Integer(), nullable=True))

    # 4. Set path_id for existing log_files based on source_id
    conn.execute(
        sa.text(
            "UPDATE log_files SET path_id = lsp.id "
            "FROM log_source_paths lsp "
            "WHERE log_files.source_id = lsp.source_id"
        )
    )

    # 5. Make path_id NOT NULL
    op.alter_column("log_files", "path_id", nullable=False)

    # 6. Add FK and index for path_id
    op.create_foreign_key(
        "fk_log_files_path_id",
        "log_files",
        "log_source_paths",
        ["path_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index(op.f("ix_log_files_path_id"), "log_files", ["path_id"], unique=False)

    # 7. Drop old UNIQUE constraint and create new one
    op.drop_constraint("uq_log_files_source_file", "log_files", type_="unique")
    op.create_unique_constraint("uq_log_files_path_file", "log_files", ["path_id", "file_name"])

    # 8. Remove base_path and file_pattern from log_sources
    op.drop_column("log_sources", "file_pattern")
    op.drop_column("log_sources", "base_path")


def downgrade() -> None:
    # 1. Re-add base_path and file_pattern to log_sources
    op.add_column(
        "log_sources",
        sa.Column("base_path", sa.String(length=1000), nullable=True),
    )
    op.add_column(
        "log_sources",
        sa.Column("file_pattern", sa.String(length=200), server_default="*.log", nullable=True),
    )

    # 2. Copy first path back to log_sources
    conn = op.get_bind()
    conn.execute(
        sa.text(
            "UPDATE log_sources SET base_path = lsp.base_path, file_pattern = lsp.file_pattern "
            "FROM (SELECT DISTINCT ON (source_id) source_id, base_path, file_pattern "
            "FROM log_source_paths ORDER BY source_id, id) lsp "
            "WHERE log_sources.id = lsp.source_id"
        )
    )
    # Set defaults for any sources that had no paths
    conn.execute(
        sa.text(
            "UPDATE log_sources SET base_path = '/', file_pattern = '*.log' WHERE base_path IS NULL"
        )
    )

    op.alter_column("log_sources", "base_path", nullable=False)
    op.alter_column("log_sources", "file_pattern", nullable=False)

    # 3. Revert UNIQUE constraint on log_files
    op.drop_constraint("uq_log_files_path_file", "log_files", type_="unique")
    op.create_unique_constraint("uq_log_files_source_file", "log_files", ["source_id", "file_name"])

    # 4. Drop path_id from log_files
    op.drop_index(op.f("ix_log_files_path_id"), table_name="log_files")
    op.drop_constraint("fk_log_files_path_id", "log_files", type_="foreignkey")
    op.drop_column("log_files", "path_id")

    # 5. Drop log_source_paths table
    op.drop_index(op.f("ix_log_source_paths_source_id"), table_name="log_source_paths")
    op.drop_table("log_source_paths")
