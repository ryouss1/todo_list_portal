"""add wiki pages

Revision ID: a1c2d3e4f5b6
Revises: b3df810d3406
Create Date: 2026-02-25

Creates: wiki_categories, wiki_tags, wiki_page_tags, wiki_pages
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSON, TSVECTOR

revision = "a1c2d3e4f5b6"
down_revision = "b3df810d3406"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── wiki_categories ───────────────────────────────────────────────────────
    op.create_table(
        "wiki_categories",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("description", sa.String(500), nullable=True),
        sa.Column("color", sa.String(7), nullable=False, server_default="#6c757d"),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_wiki_categories_name", "wiki_categories", ["name"], unique=True)

    # ── wiki_tags ─────────────────────────────────────────────────────────────
    op.create_table(
        "wiki_tags",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("slug", sa.String(100), nullable=False),
        sa.Column("color", sa.String(7), nullable=False, server_default="#6c757d"),
        sa.Column("created_by", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_wiki_tags_name", "wiki_tags", ["name"], unique=True)
    op.create_index("idx_wiki_tags_slug", "wiki_tags", ["slug"], unique=True)

    # ── wiki_pages ────────────────────────────────────────────────────────────
    op.create_table(
        "wiki_pages",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("slug", sa.String(500), nullable=False),
        sa.Column("parent_id", sa.Integer(), nullable=True),
        sa.Column("content", JSON(), nullable=False, server_default='{"type":"doc","content":[]}'),
        sa.Column("yjs_state", sa.LargeBinary(), nullable=True),
        sa.Column("author_id", sa.Integer(), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("visibility", sa.String(20), nullable=False, server_default="internal"),
        sa.Column("category_id", sa.Integer(), nullable=True),
        sa.Column("search_vector", TSVECTOR(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.ForeignKeyConstraint(["parent_id"], ["wiki_pages.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["author_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["category_id"], ["wiki_categories.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_wiki_pages_slug", "wiki_pages", ["slug"], unique=True)
    op.create_index("idx_wiki_pages_parent_id", "wiki_pages", ["parent_id"])
    op.create_index("idx_wiki_pages_author_id", "wiki_pages", ["author_id"])
    op.create_index("idx_wiki_pages_category_id", "wiki_pages", ["category_id"])
    op.create_index("idx_wiki_pages_search", "wiki_pages", ["search_vector"], postgresql_using="gin")

    # Full-text search trigger on title
    op.execute("""
        CREATE TRIGGER wiki_pages_search_update
        BEFORE INSERT OR UPDATE ON wiki_pages
        FOR EACH ROW EXECUTE FUNCTION
        tsvector_update_trigger(search_vector, 'pg_catalog.simple', title)
    """)

    # ── wiki_page_tags (junction) ─────────────────────────────────────────────
    op.create_table(
        "wiki_page_tags",
        sa.Column("page_id", sa.Integer(), nullable=False),
        sa.Column("tag_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["page_id"], ["wiki_pages.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tag_id"], ["wiki_tags.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("page_id", "tag_id"),
    )
    op.create_index("idx_wiki_page_tags_tag_id", "wiki_page_tags", ["tag_id"])


def downgrade() -> None:
    op.drop_table("wiki_page_tags")
    op.execute("DROP TRIGGER IF EXISTS wiki_pages_search_update ON wiki_pages")
    op.drop_index("idx_wiki_pages_search", table_name="wiki_pages")
    op.drop_index("idx_wiki_pages_category_id", table_name="wiki_pages")
    op.drop_index("idx_wiki_pages_author_id", table_name="wiki_pages")
    op.drop_index("idx_wiki_pages_parent_id", table_name="wiki_pages")
    op.drop_index("idx_wiki_pages_slug", table_name="wiki_pages")
    op.drop_table("wiki_pages")
    op.drop_index("idx_wiki_tags_slug", table_name="wiki_tags")
    op.drop_index("idx_wiki_tags_name", table_name="wiki_tags")
    op.drop_table("wiki_tags")
    op.drop_index("idx_wiki_categories_name", table_name="wiki_categories")
    op.drop_table("wiki_categories")
