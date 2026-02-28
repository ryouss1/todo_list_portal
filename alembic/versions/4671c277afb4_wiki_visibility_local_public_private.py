"""wiki_visibility_local_public_private

Revision ID: 4671c277afb4
Revises: f8e8afae33a0
Create Date: 2026-02-26 09:51:14.421223

変更内容:
- wiki_pages.visibility の値体系を変更
  - 旧 'internal'（全ログインユーザー）→ 新 'public'（他部署）
  - 旧 'public'（インターネット公開、廃止）→ 新 'public'（他部署）
  - 新規追加 'local'（自部署、同一グループのみ）
  - 'private'（作成者のみ）は変更なし
- server_default を 'internal' から 'local' に変更
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "4671c277afb4"
down_revision: Union[str, None] = "f8e8afae33a0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 既存の 'internal' および 'public' はどちらも新 'public'（全ログインユーザー）に変換
    op.execute("UPDATE wiki_pages SET visibility = 'public' WHERE visibility IN ('internal', 'public')")
    # server_default を 'local'（自部署）に変更
    op.alter_column(
        "wiki_pages",
        "visibility",
        existing_type=sa.String(20),
        server_default="local",
        existing_nullable=False,
    )


def downgrade() -> None:
    # ロールバック: 'local'/'public' をすべて 'internal' に戻す（lossy）
    op.execute("UPDATE wiki_pages SET visibility = 'internal' WHERE visibility IN ('local', 'public')")
    op.alter_column(
        "wiki_pages",
        "visibility",
        existing_type=sa.String(20),
        server_default="internal",
        existing_nullable=False,
    )
