"""Add wiki_attachments table (Phase 2 attachment support)

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-02-25

Changes:
- Create wiki_attachments table
  - page_id: FK → wiki_pages.id (ON DELETE CASCADE)
  - filename: original display name
  - stored_path: relative path on disk (uploads/wiki/{page_id}/{stored_filename})
  - mime_type: MIME type string
  - file_size: size in bytes
  - created_at: timestamp
"""

import sqlalchemy as sa
from alembic import op

revision = "d4e5f6a7b8c9"
down_revision = "c3d4e5f6a7b8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "wiki_attachments",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column(
            "page_id",
            sa.Integer(),
            sa.ForeignKey("wiki_pages.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("filename", sa.String(500), nullable=False),
        sa.Column("stored_path", sa.String(1000), nullable=False),
        sa.Column("mime_type", sa.String(200), nullable=True),
        sa.Column("file_size", sa.Integer(), server_default="0", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_wiki_attachments_page_id", "wiki_attachments", ["page_id"])


def downgrade() -> None:
    op.drop_index("idx_wiki_attachments_page_id", table_name="wiki_attachments")
    op.drop_table("wiki_attachments")
