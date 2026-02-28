"""wiki content column JSON to Markdown TEXT

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-02-25

Changes:
- wiki_pages.content: JSON -> TEXT (Markdown)
- wiki_pages.yjs_state: DROP (unused column)
- Data migration: convert existing Tiptap JSON content to Markdown
"""

import json
from typing import Any

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "c3d4e5f6a7b8"
down_revision = "b2c3d4e5f6a7"
branch_labels = None
depends_on = None


# ─── Tiptap JSON → Markdown converter ────────────────────────────────────────


def _tiptap_to_md(node: Any) -> str:
    """Recursively convert a Tiptap JSON node to Markdown text."""
    if not node or not isinstance(node, dict):
        return ""
    t = node.get("type", "")
    content = node.get("content") or []

    if t == "doc":
        parts = [_tiptap_to_md(c) for c in content]
        return "\n\n".join(p for p in parts if p)

    if t == "paragraph":
        return _inline_md(content)

    if t == "heading":
        level = (node.get("attrs") or {}).get("level", 1)
        return "#" * level + " " + _inline_md(content)

    if t == "bulletList":
        return "\n".join("- " + _list_item_text(item) for item in content)

    if t == "orderedList":
        return "\n".join(f"{i + 1}. " + _list_item_text(item) for i, item in enumerate(content))

    if t == "taskList":
        items = []
        for item in content:
            checked = (item.get("attrs") or {}).get("checked", False)
            check = "[x]" if checked else "[ ]"
            items.append(f"- {check} {_list_item_text(item)}")
        return "\n".join(items)

    if t == "blockquote":
        inner_parts = [_tiptap_to_md(c) for c in content]
        inner = "\n\n".join(p for p in inner_parts if p)
        return "\n".join("> " + line for line in inner.split("\n"))

    if t == "codeBlock":
        lang = ((node.get("attrs") or {}).get("language") or "")
        code = "".join(n.get("text", "") for n in content if n.get("type") == "text")
        return f"```{lang}\n{code}\n```"

    if t == "horizontalRule":
        return "---"

    if t == "hardBreak":
        return "  \n"

    if t == "text":
        text = node.get("text", "")
        for mark in node.get("marks") or []:
            mt = mark.get("type", "")
            if mt == "bold":
                text = f"**{text}**"
            elif mt == "italic":
                text = f"*{text}*"
            elif mt == "strike":
                text = f"~~{text}~~"
            elif mt == "code":
                text = f"`{text}`"
            elif mt == "link":
                href = ((mark.get("attrs") or {}).get("href") or "")
                text = f"[{text}]({href})"
        return text

    # Fallback: recurse into children
    return "".join(_tiptap_to_md(c) for c in content)


def _list_item_text(item: dict) -> str:
    """Extract text from a listItem / taskItem node."""
    item_content = item.get("content") or []
    # listItem wraps content in a paragraph node
    if item_content and item_content[0].get("type") == "paragraph":
        return _inline_md(item_content[0].get("content") or [])
    return _inline_md(item_content)


def _inline_md(nodes: list) -> str:
    return "".join(_tiptap_to_md(n) for n in nodes)


def _convert_row_content(raw: Any) -> str:
    """Convert a DB content value to Markdown string."""
    if raw is None:
        return ""
    if isinstance(raw, str):
        try:
            parsed = json.loads(raw)
            return _tiptap_to_md(parsed)
        except (json.JSONDecodeError, TypeError):
            # Already a plain string or unparseable — keep as-is
            return raw
    if isinstance(raw, dict):
        return _tiptap_to_md(raw)
    return ""


# ─── Migration ────────────────────────────────────────────────────────────────


def upgrade() -> None:
    # Step 1: Add a temporary TEXT column for Markdown content
    op.add_column("wiki_pages", sa.Column("content_md", sa.Text(), nullable=True))

    # Step 2: Migrate existing Tiptap JSON → Markdown row by row
    conn = op.get_bind()
    rows = conn.execute(sa.text("SELECT id, content FROM wiki_pages")).fetchall()
    for row in rows:
        md = _convert_row_content(row[1])
        conn.execute(
            sa.text("UPDATE wiki_pages SET content_md = :md WHERE id = :id"),
            {"md": md, "id": row[0]},
        )

    # Step 3: Drop old JSON content column
    op.drop_column("wiki_pages", "content")

    # Step 4: Rename content_md → content
    op.alter_column("wiki_pages", "content_md", new_column_name="content")

    # Step 5: Drop unused yjs_state column (real-time collaboration not implemented)
    op.drop_column("wiki_pages", "yjs_state")


def downgrade() -> None:
    # NOTE: Markdown cannot be automatically converted back to Tiptap JSON.
    # Downgrade restores the column type but content data will be lost.
    op.add_column("wiki_pages", sa.Column("yjs_state", sa.LargeBinary(), nullable=True))

    op.add_column("wiki_pages", sa.Column("content_backup", sa.Text(), nullable=True))
    conn = op.get_bind()
    conn.execute(sa.text("UPDATE wiki_pages SET content_backup = content"))

    op.drop_column("wiki_pages", "content")
    op.add_column(
        "wiki_pages",
        sa.Column(
            "content",
            postgresql.JSON(),
            nullable=False,
            server_default='{"type":"doc","content":[]}',
        ),
    )
    op.drop_column("wiki_pages", "content_backup")
