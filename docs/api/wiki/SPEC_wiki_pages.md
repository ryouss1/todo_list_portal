# WIKI ページ管理 設計書

> 本ドキュメントは [spec_wiki.md](../../spec_wiki.md) の補足資料です。
>
> フェーズ1: ページ CRUD、階層構造（ページツリー）、Alembic マイグレーション

---

## 1. 概要

### 1.1 目的

- チームのドキュメントをページ単位で管理し、階層（親子）構造でナビゲーション可能にする
- Tiptap ブロックエディタで作成した JSON コンテンツを保存・配信する
- `slug` ベースの URL でアクセス可能にする（例: `/wiki/dev/api-design`）

### 1.2 主要機能

| 機能 | 説明 |
|------|------|
| ページ CRUD | タイトル・コンテンツ・親ページを指定して作成・更新・削除 |
| ページツリー | サイドバーに折りたたみ可能な親子ツリーを表示 |
| スラッグ生成 | タイトルから自動生成、または手動指定。UNIQUE 制約 |
| 公開範囲 | `internal`（認証ユーザー）/ `public`（未認証も閲覧可） / `private`（作成者のみ） |
| 並び順 | `sort_order` で同一親配下のページ順序を制御 |
| ブレッドクラム | 親→子の階層パスを URL・UI 両方で表現 |
| カテゴリ | 大分類の単一設定（詳細: [SPEC_wiki_tags_categories.md](./SPEC_wiki_tags_categories.md)） |
| タグ | 複数キーワードによる横断分類（詳細: [SPEC_wiki_tags_categories.md](./SPEC_wiki_tags_categories.md)） |

---

## 2. データモデル

### 2.1 ER 図

```
users            (1) ──── (N) wiki_pages.author_id              (SET NULL)
wiki_pages       (1) ──── (N) wiki_pages.parent_id              (SET NULL, 自己参照)
wiki_categories  (1) ──── (N) wiki_pages.category_id            (SET NULL)
wiki_pages       (N) ──── (N) wiki_tags                         (wiki_page_tags 経由)
wiki_pages       (N) ──── (N) task_list_items                   (wiki_page_task_items 経由, CASCADE)
wiki_pages       (N) ──── (N) tasks                             (wiki_page_tasks 経由, SET NULL)
wiki_pages       (1) ──── (N) wiki_attachments.page_id          (CASCADE, Phase 2)
users            (1) ──── (N) wiki_attachments.uploaded_by      (SET NULL, Phase 2)
users            (1) ──── (N) wiki_page_task_items.linked_by    (SET NULL)
users            (1) ──── (N) wiki_page_tasks.linked_by         (SET NULL)
```

> タグ・カテゴリの詳細スキーマは [SPEC_wiki_tags_categories.md](./SPEC_wiki_tags_categories.md) を参照。
> タスク紐づけの詳細スキーマは [SPEC_wiki_task_links.md](./SPEC_wiki_task_links.md) を参照。
> 添付ファイルの詳細スキーマは [SPEC_wiki_attachments.md](./SPEC_wiki_attachments.md) を参照（Phase 2）。

### 2.2 wiki_pages テーブル

WIKI ページのコンテンツと階層構造を管理する。

| カラム名 | 型 | 制約 | 説明 |
|----------|-----|------|------|
| id | Integer | PK, AUTO_INCREMENT | ページ ID |
| title | String(500) | NOT NULL | ページタイトル |
| slug | String(500) | NOT NULL, UNIQUE, INDEX | URL スラッグ（例: `dev-api-design`） |
| parent_id | Integer | FK(wiki_pages.id, SET NULL), NULL 許可, INDEX | 親ページ ID（NULL = ルートページ） |
| content | JSON | NOT NULL, DEFAULT `'{"type":"doc","content":[]}'` | Tiptap JSON コンテンツ |
| yjs_state | LargeBinary | NULL 許可 | Yjs CRDT バイナリ状態（フェーズ3で使用） |
| author_id | Integer | FK(users.id, SET NULL), NULL 許可, INDEX | 作成者 ID |
| sort_order | Integer | NOT NULL, DEFAULT 0 | 同一親配下での表示順 |
| visibility | String(20) | NOT NULL, DEFAULT `'internal'` | 公開範囲 |
| category_id | Integer | FK(wiki_categories.id, SET NULL), NULL 許可, INDEX | カテゴリ ID |
| search_vector | TSVECTOR | NULL 許可 | 全文検索インデックス（PostgreSQL トリガーで自動更新） |
| created_at | DateTime(TZ) | DEFAULT now() | 作成日時 |
| updated_at | DateTime(TZ) | DEFAULT now(), ON UPDATE now() | 更新日時 |

- モデルファイル: `app/models/wiki_page.py`

**visibility 値:**

| 値 | 説明 | アクセス |
|----|------|---------|
| `internal` | 内部公開（デフォルト） | 認証済みユーザー全員 |
| `public` | 公開 | 未認証ユーザーも閲覧可 |
| `private` | 非公開 | 作成者と admin のみ |

### 2.3 slug 生成ルール

- タイトルから自動生成: `title.lower()` → スペース・記号を `-` に変換 → 英数字・ハイフンのみ残す
- 日本語タイトルは UUID ベースのスラッグを自動生成（`wiki-{uuid4_short}`）
- 衝突時: `-2`, `-3` を末尾に付与して一意性を保証

```python
import re
import unicodedata

def generate_slug(title: str) -> str:
    # NFKCで正規化（全角英数字→半角）
    title = unicodedata.normalize("NFKC", title)
    # 英数字・スペース・ハイフン以外を除去
    slug = re.sub(r"[^\w\s-]", "", title.lower())
    # スペース・アンダースコアをハイフンに変換
    slug = re.sub(r"[-\s_]+", "-", slug).strip("-")
    if not slug:
        import uuid
        slug = f"wiki-{str(uuid.uuid4())[:8]}"
    return slug
```

---

## 3. API エンドポイント

### 3.1 一覧

| メソッド | パス | 説明 | 認証 |
|---------|------|------|------|
| GET | `/api/wiki/pages` | ページツリー取得（全階層） | 必要 |
| GET | `/api/wiki/pages/roots` | ルートページ一覧取得 | 必要 |
| POST | `/api/wiki/pages` | ページ作成 | 必要 |
| GET | `/api/wiki/pages/{id}` | ページ取得（ID 指定） | 必要 |
| GET | `/api/wiki/pages/by-slug/{slug}` | ページ取得（スラッグ指定） | 必要 |
| PUT | `/api/wiki/pages/{id}` | ページ更新 | 必要（作成者 or admin） |
| DELETE | `/api/wiki/pages/{id}` | ページ削除 | 必要（作成者 or admin） |
| GET | `/api/wiki/pages/{id}/children` | 子ページ一覧取得 | 必要 |
| PUT | `/api/wiki/pages/{id}/move` | ページ移動（親変更・並び順変更） | 必要（作成者 or admin） |

### 3.2 GET /api/wiki/pages

ページのツリー構造を取得する。

- **クエリパラメータ:**

| パラメータ | 型 | デフォルト | 説明 |
|------------|-----|-----------|------|
| flat | boolean | false | true の場合フラットリストで返却 |

- **レスポンス:** `200 OK` - `WikiPageTreeNode[]`

```json
[
  {
    "id": 1,
    "title": "開発ガイド",
    "slug": "dev-guide",
    "parent_id": null,
    "sort_order": 0,
    "visibility": "internal",
    "author_id": 1,
    "updated_at": "2026-02-25T10:00:00+09:00",
    "children": [
      {
        "id": 2,
        "title": "API 設計",
        "slug": "dev-api-design",
        "parent_id": 1,
        "sort_order": 0,
        "children": []
      }
    ]
  }
]
```

### 3.3 POST /api/wiki/pages

ページを新規作成する。

- **リクエストボディ:** `WikiPageCreate`

| フィールド | 型 | 必須 | デフォルト | 説明 |
|------------|-----|------|-----------|------|
| title | string | Yes | - | ページタイトル |
| slug | string | No | 自動生成 | URL スラッグ（省略時はタイトルから自動生成） |
| parent_id | integer | No | null | 親ページ ID |
| content | object | No | `{"type":"doc","content":[]}` | Tiptap JSON コンテンツ |
| sort_order | integer | No | 0 | 表示順 |
| visibility | string | No | `"internal"` | 公開範囲 |

- **レスポンス:** `201 Created` - `WikiPageResponse`
- **エラー:**
  - `400 Bad Request` - スラッグ重複、無効な parent_id（循環参照）
  - `422 Unprocessable Entity` - バリデーションエラー

### 3.4 GET /api/wiki/pages/{id}

指定 ID のページを取得する。`content`（Tiptap JSON）を含む詳細レスポンス。

- **レスポンス:** `200 OK` - `WikiPageDetailResponse`
- **エラー:** `404 Not Found`

### 3.5 GET /api/wiki/pages/by-slug/{slug}

スラッグでページを取得する。URL ルーティング用。

- **レスポンス:** `200 OK` - `WikiPageDetailResponse`
- **エラー:** `404 Not Found`

### 3.6 PUT /api/wiki/pages/{id}

ページを更新する。

- **リクエストボディ:** `WikiPageUpdate`（全フィールド任意）

| フィールド | 型 | 説明 |
|------------|-----|------|
| title | string | ページタイトル |
| slug | string | URL スラッグ（変更時は UNIQUE チェック） |
| content | object | Tiptap JSON コンテンツ |
| sort_order | integer | 表示順 |
| visibility | string | 公開範囲 |

- **レスポンス:** `200 OK` - `WikiPageResponse`
- **エラー:** `403 Forbidden` - 権限なし / `404 Not Found`

### 3.7 DELETE /api/wiki/pages/{id}

ページを削除する。子ページの `parent_id` は SET NULL（ルートページに昇格）。

- **レスポンス:** `204 No Content`
- **エラー:** `403 Forbidden` - 権限なし / `404 Not Found`

### 3.8 PUT /api/wiki/pages/{id}/move

ページの親ページや並び順を変更する（ドラッグ&ドロップ並び替え用）。

- **リクエストボディ:** `WikiPageMove`

| フィールド | 型 | 必須 | 説明 |
|------------|-----|------|------|
| parent_id | integer \| null | No | 新しい親ページ ID（null = ルートに移動） |
| sort_order | integer | No | 新しい表示順 |

- **レスポンス:** `200 OK` - `WikiPageResponse`
- **エラー:** `400 Bad Request` - 循環参照 / `403 Forbidden` / `404 Not Found`

---

## 4. スキーマ

### 4.1 WikiPageResponse

ページ一覧・更新・削除レスポンスに使用（`content` は含まない）。

| フィールド | 型 | 説明 |
|------------|-----|------|
| id | integer | ページ ID |
| title | string | タイトル |
| slug | string | URL スラッグ |
| parent_id | integer \| null | 親ページ ID |
| author_id | integer \| null | 作成者 ID |
| author_name | string \| null | 作成者表示名 |
| sort_order | integer | 表示順 |
| visibility | string | 公開範囲 |
| created_at | datetime | 作成日時 |
| updated_at | datetime | 更新日時 |

### 4.2 WikiPageDetailResponse

個別ページ取得レスポンス（`content` を含む）。

`WikiPageResponse` の全フィールド + 以下:

| フィールド | 型 | 説明 |
|------------|-----|------|
| content | object | Tiptap JSON コンテンツ |
| breadcrumbs | WikiBreadcrumb[] | ルートからのパス（順序付き） |

### 4.3 WikiBreadcrumb

| フィールド | 型 | 説明 |
|------------|-----|------|
| id | integer | ページ ID |
| title | string | タイトル |
| slug | string | URL スラッグ |

### 4.4 WikiPageTreeNode

ツリー取得レスポンスに使用。

`WikiPageResponse` の全フィールド + 以下:

| フィールド | 型 | 説明 |
|------------|-----|------|
| children | WikiPageTreeNode[] | 子ページ一覧（再帰） |

---

## 5. ページ階層の実装

### 5.1 ツリー取得の実装方針

再帰 CTE（Common Table Expression）を使用してツリー全体を 1 クエリで取得する。

```python
# app/crud/wiki_page.py

from sqlalchemy import text
from typing import List, Optional
from app.models.wiki_page import WikiPage

def get_tree(db) -> List[dict]:
    """全ページをツリー構造で取得（PostgreSQL CTE 使用）"""
    rows = db.execute(text("""
        WITH RECURSIVE tree AS (
            -- ルートページ
            SELECT id, title, slug, parent_id, sort_order, visibility,
                   author_id, created_at, updated_at, 0 AS depth
            FROM wiki_pages
            WHERE parent_id IS NULL

            UNION ALL

            -- 子ページ
            SELECT wp.id, wp.title, wp.slug, wp.parent_id, wp.sort_order,
                   wp.visibility, wp.author_id, wp.created_at, wp.updated_at,
                   tree.depth + 1
            FROM wiki_pages wp
            INNER JOIN tree ON wp.parent_id = tree.id
        )
        SELECT * FROM tree ORDER BY depth, sort_order, id
    """)).fetchall()
    return _build_tree(rows)


def _build_tree(rows: list) -> list:
    """フラットリストを親子ツリーに変換"""
    node_map = {}
    roots = []
    for row in rows:
        node = dict(row._mapping)
        node["children"] = []
        node_map[node["id"]] = node
        if node["parent_id"] is None:
            roots.append(node)
        else:
            parent = node_map.get(node["parent_id"])
            if parent:
                parent["children"].append(node)
    return roots
```

### 5.2 循環参照の検出

`parent_id` を変更する際は、新しい親が現在ページの子孫でないことを確認する。

```python
def is_descendant(db, ancestor_id: int, candidate_id: int) -> bool:
    """candidate_id が ancestor_id の子孫かどうかを確認"""
    result = db.execute(text("""
        WITH RECURSIVE descendants AS (
            SELECT id FROM wiki_pages WHERE id = :ancestor_id
            UNION ALL
            SELECT wp.id FROM wiki_pages wp
            INNER JOIN descendants d ON wp.parent_id = d.id
        )
        SELECT 1 FROM descendants WHERE id = :candidate_id
    """), {"ancestor_id": ancestor_id, "candidate_id": candidate_id}).fetchone()
    return result is not None
```

### 5.3 ブレッドクラムの生成

```python
def get_breadcrumbs(db, page_id: int) -> list:
    """ルートからのパスを取得"""
    result = db.execute(text("""
        WITH RECURSIVE ancestors AS (
            SELECT id, title, slug, parent_id, 0 AS depth
            FROM wiki_pages WHERE id = :page_id
            UNION ALL
            SELECT wp.id, wp.title, wp.slug, wp.parent_id, a.depth + 1
            FROM wiki_pages wp
            INNER JOIN ancestors a ON wp.id = a.parent_id
        )
        SELECT id, title, slug FROM ancestors ORDER BY depth DESC
    """), {"page_id": page_id}).fetchall()
    return [{"id": r.id, "title": r.title, "slug": r.slug} for r in result]
```

---

## 6. フロントエンド: ページツリー

### 6.1 サイドバーツリー UI

- **ファイル:** `templates/wiki.html`（共通レイアウト）
- **実装:** Vanilla JS（ライブラリ依存なし）

**HTML 構造（案）:**

```html
<div id="wiki-sidebar">
  <div class="wiki-sidebar-header">
    <span>WIKI</span>
    <button onclick="openNewPageModal(null)">+ 新規</button>
  </div>
  <div id="wiki-tree"></div>
</div>
```

**JS（ツリー描画）:**

```javascript
// static/js/wiki.js

function renderTree(nodes, container, depth = 0) {
  nodes.forEach(node => {
    const item = document.createElement("div");
    item.className = "wiki-tree-item";
    item.style.paddingLeft = `${depth * 16}px`;
    item.innerHTML = `
      <span class="wiki-tree-toggle ${node.children.length ? '' : 'invisible'}">
        <i class="bi bi-chevron-right"></i>
      </span>
      <a href="/wiki/${node.slug}" class="wiki-tree-link">${escapeHtml(node.title)}</a>
      <button class="wiki-tree-add" onclick="openNewPageModal(${node.id})">+</button>
    `;
    container.appendChild(item);

    if (node.children.length > 0) {
      const childContainer = document.createElement("div");
      childContainer.className = "wiki-tree-children collapse";
      renderTree(node.children, childContainer, depth + 1);
      container.appendChild(childContainer);

      // 折りたたみトグル
      item.querySelector(".wiki-tree-toggle").addEventListener("click", () => {
        childContainer.classList.toggle("show");
        item.querySelector(".bi").classList.toggle("bi-chevron-right");
        item.querySelector(".bi").classList.toggle("bi-chevron-down");
      });
    }
  });
}

async function loadTree() {
  const res = await fetch("/api/wiki/pages");
  const tree = await res.json();
  const container = document.getElementById("wiki-tree");
  container.innerHTML = "";
  renderTree(tree, container);
}
```

### 6.2 ブレッドクラム

```html
<nav aria-label="breadcrumb">
  <ol class="breadcrumb">
    <li class="breadcrumb-item"><a href="/wiki">WIKI</a></li>
    {% for crumb in page.breadcrumbs %}
      {% if loop.last %}
        <li class="breadcrumb-item active">{{ crumb.title }}</li>
      {% else %}
        <li class="breadcrumb-item"><a href="/wiki/{{ crumb.slug }}">{{ crumb.title }}</a></li>
      {% endif %}
    {% endfor %}
  </ol>
</nav>
```

---

## 7. 画面仕様

### 7.1 画面一覧

| URL | 説明 | テンプレート |
|-----|------|------------|
| `/wiki` | WIKI トップ（最近更新ページ一覧） | `templates/wiki.html` |
| `/wiki/{slug}` | ページ閲覧 | `templates/wiki.html` |
| `/wiki/{slug}/edit` | ページ編集（Tiptap エディタ） | `templates/wiki_edit.html` |
| `/wiki/new` | 新規ページ作成 | `templates/wiki_edit.html` |

### 7.2 /wiki トップページ

- **ヘッダー:** 「最近更新されたページ」一覧（最新10件）
- **サイドバー:** ページツリー（全ページ）
- **ボタン:** 「新規ページ作成」

### 7.3 /wiki/{slug} ページ閲覧

- **左サイドバー（幅 250px）:** ページツリー。現在ページをハイライト
- **メインエリア:** ページタイトル + ブレッドクラム + Tiptap 表示（読み取り専用）
- **ヘッダー右:** 「編集」ボタン（認証ユーザーのみ）、「削除」ボタン（作成者 or admin）
- **メタ情報:** 作成者名、最終更新日時

### 7.4 /wiki/{slug}/edit ページ編集

- **Tiptap エディタ:** 編集可能モード（`static/js/wiki.js` で初期化）
- **タイトル入力:** エディタ上部に独立した `<input>` フィールド
- **スラッグ入力:** タイトル変更時に自動更新、手動変更も可
- **保存ボタン:** `PUT /api/wiki/pages/{id}` に JSON で送信
- **親ページ設定:** ドロップダウン（任意）
- **公開範囲設定:** セレクトボックス（internal/public/private）
- **キャンセル:** ページ閲覧に戻る
- **削除ボタン:** 既存ページ編集時のみ表示（新規作成時は非表示）

#### 削除フロー

1. ユーザーが「削除」ボタン（赤枠）をクリック
2. Bootstrap モーダルで確認ダイアログを表示
   - ページタイトルを表示
   - 「子ページはルートに昇格する」旨の警告を表示
3. 「削除する」ボタンをクリック → `DELETE /api/wiki/pages/{id}` を呼び出し
4. 成功時: `/wiki` にリダイレクト
5. 失敗時: エラートーストを表示してモーダルを閉じる

```
┌──────────────────────────────────────────┐
│  ⚠ ページを削除                         ×  │
├──────────────────────────────────────────┤
│  以下のページを削除しますか？               │
│  この操作は元に戻せません。                 │
│                                          │
│  「API 設計ガイド」                        │
│                                          │
│  ℹ 子ページがある場合、ルートに昇格します。  │
├──────────────────────────────────────────┤
│               [キャンセル] [🗑 削除する]   │
└──────────────────────────────────────────┘
```

**実装:** `WikiEditor.delete()` / `WikiEditor.confirmDelete()` in `static/js/wiki.js`

---

## 8. 認可ルール

| 操作 | 必要権限 |
|------|---------|
| ページ閲覧（internal） | 認証済みユーザー |
| ページ閲覧（public） | 不要 |
| ページ閲覧（private） | 作成者 or admin |
| ページ作成 | 認証済みユーザー |
| ページ更新 | 作成者 or admin |
| ページ削除 | 作成者 or admin |
| ページ移動 | 作成者 or admin |

---

## 9. Alembic マイグレーション

### 9.1 マイグレーションファイル

```python
# alembic/versions/xxxx_add_wiki_pages.py
"""add wiki_pages table

Revision ID: xxxx
Revises: b3df810d3406
Create Date: 2026-xx-xx
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSON, TSVECTOR

def upgrade() -> None:
    op.create_table(
        "wiki_pages",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("slug", sa.String(500), nullable=False),
        sa.Column("parent_id", sa.Integer(), sa.ForeignKey("wiki_pages.id", ondelete="SET NULL"), nullable=True),
        sa.Column("content", JSON(), nullable=False, server_default='{"type":"doc","content":[]}'),
        sa.Column("yjs_state", sa.LargeBinary(), nullable=True),
        sa.Column("author_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("visibility", sa.String(20), nullable=False, server_default="internal"),
        sa.Column("category_id", sa.Integer(), sa.ForeignKey("wiki_categories.id", ondelete="SET NULL"), nullable=True),
        sa.Column("search_vector", TSVECTOR(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    op.create_index("idx_wiki_pages_slug", "wiki_pages", ["slug"], unique=True)
    op.create_index("idx_wiki_pages_parent_id", "wiki_pages", ["parent_id"])
    op.create_index("idx_wiki_pages_author_id", "wiki_pages", ["author_id"])
    op.create_index("idx_wiki_pages_category_id", "wiki_pages", ["category_id"])
    op.create_index("idx_wiki_pages_search", "wiki_pages", ["search_vector"], postgresql_using="gin")

    # 全文検索トリガー（詳細は SPEC_wiki_search.md を参照）
    op.execute("""
        CREATE TRIGGER wiki_pages_search_update
        BEFORE INSERT OR UPDATE ON wiki_pages
        FOR EACH ROW EXECUTE FUNCTION
        tsvector_update_trigger(search_vector, 'pg_catalog.simple', title)
    """)


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS wiki_pages_search_update ON wiki_pages")
    op.drop_index("idx_wiki_pages_category_id", table_name="wiki_pages")
    op.drop_table("wiki_pages")
```

### 9.2 SQLAlchemy モデル

```python
# app/models/wiki_page.py
from sqlalchemy import Column, Integer, String, JSON, LargeBinary, DateTime, ForeignKey, Index
from sqlalchemy.dialects.postgresql import TSVECTOR
from sqlalchemy.orm import relationship
from portal_core.database import Base
import sqlalchemy as sa


class WikiPage(Base):
    __tablename__ = "wiki_pages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(500), nullable=False)
    slug = Column(String(500), nullable=False, unique=True, index=True)
    parent_id = Column(Integer, ForeignKey("wiki_pages.id", ondelete="SET NULL"), nullable=True, index=True)
    content = Column(JSON, nullable=False, server_default='{"type":"doc","content":[]}')
    yjs_state = Column(LargeBinary, nullable=True)
    author_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    sort_order = Column(Integer, nullable=False, server_default="0")
    visibility = Column(String(20), nullable=False, server_default="internal")
    category_id = Column(Integer, ForeignKey("wiki_categories.id", ondelete="SET NULL"), nullable=True, index=True)
    search_vector = Column(TSVECTOR, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=sa.func.now())
    updated_at = Column(DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now())

    # 自己参照リレーション
    children = relationship(
        "WikiPage",
        backref=sa.orm.backref("parent", remote_side=[id]),
        foreign_keys=[parent_id],
        order_by="WikiPage.sort_order",
    )
    author = relationship("User", foreign_keys=[author_id])
    category = relationship("WikiCategory", foreign_keys=[category_id])

    __table_args__ = (
        Index("idx_wiki_pages_search", search_vector, postgresql_using="gin"),
    )
```

---

## 10. 実装ファイル一覧（フェーズ1）

| ファイル | 種別 | 説明 |
|---------|------|------|
| `alembic/versions/xxxx_add_wiki_pages.py` | マイグレーション | `wiki_pages` テーブル作成 |
| `app/models/wiki_page.py` | モデル | WikiPage ORM モデル |
| `app/schemas/wiki_page.py` | スキーマ | Request/Response Pydantic モデル |
| `app/crud/wiki_page.py` | CRUD | ページ CRUD + ツリー取得 + ブレッドクラム |
| `app/services/wiki_service.py` | サービス | ビジネスロジック（slug 生成、循環参照チェック等） |
| `app/routers/api_wiki.py` | ルーター | API エンドポイント |
| `app/routers/pages.py` | ルーター | ページルート（`/wiki/*`） |
| `templates/wiki.html` | テンプレート | WIKI 閲覧画面（サイドバーツリー付き） |
| `templates/wiki_edit.html` | テンプレート | WIKI 編集画面（Tiptap エディタ） |
| `static/js/wiki.js` | JS | ページツリー + 保存 + ナビゲーション |
| `tests/test_wiki.py` | テスト | pytest テストケース |

---

## 11. テスト方針

### 11.1 テストケース（予定）

| # | テストケース | 確認内容 |
|---|------------|---------|
| 1 | ページ作成 | 201 Created、slug 自動生成 |
| 2 | スラッグ重複 | 400 Bad Request |
| 3 | 親子ページ作成 | parent_id が正しく設定される |
| 4 | ツリー取得 | 階層構造が正しく再構築される |
| 5 | ブレッドクラム | ルートからのパスが正しい |
| 6 | 循環参照チェック | 子ページを親に設定しようとすると 400 |
| 7 | 削除時の子ページ | parent_id が NULL になる（SET NULL） |
| 8 | visibility=private | 作成者以外は 404 |
| 9 | ページ更新 | content（Tiptap JSON）が正しく保存される |
| 10 | 移動（sort_order 変更） | sort_order が更新される |
| 11 | 権限なし更新 | 403 Forbidden |
| 12 | 未認証アクセス（internal） | 401 Unauthorized |
| 13 | 未認証アクセス（public） | 200 OK |
| 14 | ページ削除（作成者） | 204 No Content、`/wiki` にリダイレクト |
| 15 | ページ削除（権限なし） | 403 Forbidden |
| 16 | 削除時の子ページ昇格 | 子ページの parent_id が NULL になる |

---

## 12. 技術的負債・今後の課題

| 項目 | 内容 | 優先度 |
|------|------|--------|
| yjs_state の利用 | フェーズ1では未使用（カラムのみ追加、フェーズ3で実装） | 低 |
| 画像埋め込み | Module 7（添付ファイル）実装後に対応 | 中（フェーズ2） |
| バージョン管理 | Module 5 実装後に編集履歴保存を追加 | 中（フェーズ2） |
| ドラッグ&ドロップ | sort_order の変更 UI。フロントエンドのみの作業 | 低 |
| `public` ページの認証なしアクセス | `app_auth_middleware` の公開パス設定が必要 | 中 |
