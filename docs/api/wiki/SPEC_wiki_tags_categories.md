# WIKI タグ・カテゴリ設計書

> 本ドキュメントは [spec_wiki.md](../../spec_wiki.md) の補足資料です。
>
> フェーズ1追加: タグ（多対多）とカテゴリ（単一分類）によるページ分類機能

---

## 1. 概要

### 1.1 目的

ページ階層（`parent_id`）だけでは表現できない横断的な分類を提供する。

| 機能 | 用途 | 設計 |
|------|------|------|
| **タグ** | 複数キーワードによる横断分類 | `wiki_tags` + `wiki_page_tags`（多対多） |
| **カテゴリ** | 大分類による一覧グルーピング | `wiki_categories`（単一分類） |

### 1.2 設計方針

| 方針 | 内容 |
|------|------|
| タグ作成 | 認証ユーザー全員が作成可能（乱立防止のため admin による削除は可） |
| カテゴリ CUD | admin のみ（マスターデータとして管理） |
| 既存テーブル | `task_categories` は流用しない（WIKI 専用テーブルを作成） |
| 検索連携 | タグ・カテゴリをフィルタ条件として `GET /api/wiki/pages` に追加 |
| 全文検索 | タグ名は `search_vector` には含めない（フィルタ API で対応） |

---

## 2. データモデル

### 2.1 ER 図

```
wiki_categories (1) ──── (N) wiki_pages.category_id  (SET NULL)
wiki_pages      (N) ──── (N) wiki_tags  （wiki_page_tags 中間テーブル経由）
```

### 2.2 wiki_categories テーブル

WIKI ページの大分類マスタ。

| カラム名 | 型 | 制約 | 説明 |
|----------|-----|------|------|
| id | Integer | PK, AUTO_INCREMENT | カテゴリ ID |
| name | String(100) | NOT NULL, UNIQUE | カテゴリ名（例: 開発, 運用, 人事） |
| description | String(500) | NULL 許可 | 説明 |
| color | String(7) | NOT NULL, DEFAULT `'#6c757d'` | 表示色（`#RRGGBB`） |
| sort_order | Integer | NOT NULL, DEFAULT 0 | 表示順 |
| created_at | DateTime(TZ) | DEFAULT now() | 作成日時 |

- モデルファイル: `app/models/wiki_category.py`

### 2.3 wiki_tags テーブル

WIKI ページに付与するタグマスタ。

| カラム名 | 型 | 制約 | 説明 |
|----------|-----|------|------|
| id | Integer | PK, AUTO_INCREMENT | タグ ID |
| name | String(100) | NOT NULL, UNIQUE | タグ名（例: API, Python, セキュリティ） |
| slug | String(100) | NOT NULL, UNIQUE, INDEX | URL 用スラッグ（例: `api`, `python`） |
| color | String(7) | NOT NULL, DEFAULT `'#6c757d'` | タグバッジ色 |
| created_by | Integer | FK(users.id, SET NULL), NULL 許可 | 作成者 ID |
| created_at | DateTime(TZ) | DEFAULT now() | 作成日時 |

- モデルファイル: `app/models/wiki_tag.py`

### 2.4 wiki_page_tags テーブル（中間テーブル）

ページとタグの多対多リレーション。

| カラム名 | 型 | 制約 | 説明 |
|----------|-----|------|------|
| page_id | Integer | FK(wiki_pages.id, CASCADE), PK | ページ ID |
| tag_id | Integer | FK(wiki_tags.id, CASCADE), PK | タグ ID |

- 複合 PK: `(page_id, tag_id)`
- INDEX: `tag_id`（タグでページを逆引きするためのインデックス）

### 2.5 wiki_pages テーブルへの追加カラム

```sql
ALTER TABLE wiki_pages
  ADD COLUMN category_id INTEGER REFERENCES wiki_categories(id) ON DELETE SET NULL;

CREATE INDEX idx_wiki_pages_category_id ON wiki_pages(category_id);
```

---

## 3. API エンドポイント

### 3.1 カテゴリ API

| メソッド | パス | 説明 | 認証 |
|---------|------|------|------|
| GET | `/api/wiki/categories` | カテゴリ一覧取得 | 必要 |
| POST | `/api/wiki/categories` | カテゴリ作成 | 必要（admin） |
| PUT | `/api/wiki/categories/{id}` | カテゴリ更新 | 必要（admin） |
| DELETE | `/api/wiki/categories/{id}` | カテゴリ削除 | 必要（admin） |

#### GET /api/wiki/categories

カテゴリ一覧を `sort_order` 昇順で取得する。各カテゴリのページ数を含む。

- **レスポンス:** `200 OK` - `WikiCategoryResponse[]`

```json
[
  { "id": 1, "name": "開発", "color": "#0d6efd", "sort_order": 0, "page_count": 5 },
  { "id": 2, "name": "運用", "color": "#198754", "sort_order": 1, "page_count": 3 }
]
```

#### POST /api/wiki/categories

- **リクエストボディ:** `WikiCategoryCreate`

| フィールド | 型 | 必須 | デフォルト |
|------------|-----|------|-----------|
| name | string | Yes | - |
| description | string | No | null |
| color | string | No | `"#6c757d"` |
| sort_order | integer | No | 0 |

- **レスポンス:** `201 Created`
- **エラー:** `400 Bad Request` - 名前重複

### 3.2 タグ API

| メソッド | パス | 説明 | 認証 |
|---------|------|------|------|
| GET | `/api/wiki/tags` | タグ一覧取得 | 必要 |
| POST | `/api/wiki/tags` | タグ作成 | 必要（全ユーザー） |
| DELETE | `/api/wiki/tags/{id}` | タグ削除 | 必要（admin） |

#### GET /api/wiki/tags

タグ一覧を名前の昇順で取得する。各タグのページ数を含む。

- **クエリパラメータ:**

| パラメータ | 型 | 説明 |
|------------|-----|------|
| q | string | タグ名の部分一致フィルタ（サジェスト用） |

- **レスポンス:** `200 OK` - `WikiTagResponse[]`

```json
[
  { "id": 1, "name": "API", "slug": "api", "color": "#6c757d", "page_count": 4 },
  { "id": 2, "name": "Python", "slug": "python", "color": "#3776ab", "page_count": 7 }
]
```

#### POST /api/wiki/tags

- **リクエストボディ:** `WikiTagCreate`

| フィールド | 型 | 必須 | デフォルト |
|------------|-----|------|-----------|
| name | string | Yes | - |
| color | string | No | `"#6c757d"` |

- スラッグはサーバー側で `name` から自動生成
- **レスポンス:** `201 Created`
- **エラー:** `400 Bad Request` - タグ名重複

### 3.3 ページへのタグ・カテゴリ操作 API

| メソッド | パス | 説明 | 認証 |
|---------|------|------|------|
| PUT | `/api/wiki/pages/{id}/tags` | ページのタグ一括更新 | 必要（作成者 or admin） |
| GET | `/api/wiki/pages?tag={slug}` | タグでページフィルタ | 必要 |
| GET | `/api/wiki/pages?category_id={id}` | カテゴリでページフィルタ | 必要 |

#### PUT /api/wiki/pages/{id}/tags

ページのタグを一括置き換えする（全削除→再追加）。

- **リクエストボディ:**

```json
{ "tag_ids": [1, 3, 5] }
```

- **レスポンス:** `200 OK` - `WikiPageResponse`（`tags` フィールド含む）

#### GET /api/wiki/pages（フィルタ拡張）

既存エンドポイントにクエリパラメータを追加する。

| パラメータ | 型 | 説明 |
|------------|-----|------|
| tag | string | タグスラッグでフィルタ（例: `?tag=api`） |
| category_id | integer | カテゴリ ID でフィルタ |
| tag_ids | List[integer] | 複数タグ ID（AND 条件: 全て含むページ） |

---

## 4. スキーマ

### 4.1 WikiCategoryResponse

| フィールド | 型 | 説明 |
|------------|-----|------|
| id | integer | カテゴリ ID |
| name | string | カテゴリ名 |
| description | string \| null | 説明 |
| color | string | 表示色 |
| sort_order | integer | 表示順 |
| page_count | integer | 所属ページ数 |

### 4.2 WikiTagResponse

| フィールド | 型 | 説明 |
|------------|-----|------|
| id | integer | タグ ID |
| name | string | タグ名 |
| slug | string | URL スラッグ |
| color | string | タグバッジ色 |
| page_count | integer | 付与ページ数 |

### 4.3 WikiPageResponse の拡張

タグとカテゴリのフィールドを追加する。

| フィールド 追加 | 型 | 説明 |
|----------------|-----|------|
| category_id | integer \| null | カテゴリ ID |
| category_name | string \| null | カテゴリ名 |
| category_color | string \| null | カテゴリ表示色 |
| tags | WikiTagResponse[] | 付与タグ一覧 |

---

## 5. 実装

### 5.1 SQLAlchemy モデル

```python
# app/models/wiki_category.py
from sqlalchemy import Column, Integer, String, DateTime
from portal_core.database import Base
import sqlalchemy as sa


class WikiCategory(Base):
    __tablename__ = "wiki_categories"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False, unique=True)
    description = Column(String(500), nullable=True)
    color = Column(String(7), nullable=False, server_default="#6c757d")
    sort_order = Column(Integer, nullable=False, server_default="0")
    created_at = Column(DateTime(timezone=True), server_default=sa.func.now())
```

```python
# app/models/wiki_tag.py
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Table
from sqlalchemy.orm import relationship
from portal_core.database import Base
import sqlalchemy as sa

# 中間テーブル
wiki_page_tags = Table(
    "wiki_page_tags",
    Base.metadata,
    Column("page_id", Integer, ForeignKey("wiki_pages.id", ondelete="CASCADE"), primary_key=True),
    Column("tag_id",  Integer, ForeignKey("wiki_tags.id",  ondelete="CASCADE"), primary_key=True),
)


class WikiTag(Base):
    __tablename__ = "wiki_tags"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False, unique=True)
    slug = Column(String(100), nullable=False, unique=True, index=True)
    color = Column(String(7), nullable=False, server_default="#6c757d")
    created_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=sa.func.now())
```

```python
# app/models/wiki_page.py への追記（既存モデルに追加）

from app.models.wiki_tag import wiki_page_tags, WikiTag
from sqlalchemy.orm import relationship

class WikiPage(Base):
    # ... 既存フィールド ...
    category_id = Column(Integer, ForeignKey("wiki_categories.id", ondelete="SET NULL"), nullable=True, index=True)

    # リレーション
    category = relationship("WikiCategory", foreign_keys=[category_id])
    tags = relationship("WikiTag", secondary=wiki_page_tags, lazy="selectin")
```

### 5.2 CRUD 実装

```python
# app/crud/wiki_tag.py

from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models.wiki_tag import WikiTag, wiki_page_tags
from app.models.wiki_page import WikiPage


def get_all_tags(db: Session, q: Optional[str] = None) -> list:
    query = db.query(
        WikiTag,
        func.count(wiki_page_tags.c.page_id).label("page_count"),
    ).outerjoin(wiki_page_tags, WikiTag.id == wiki_page_tags.c.tag_id)

    if q:
        query = query.filter(WikiTag.name.ilike(f"%{q}%"))

    return query.group_by(WikiTag.id).order_by(WikiTag.name).all()


def update_page_tags(db: Session, page_id: int, tag_ids: list[int]) -> WikiPage:
    """ページのタグを一括置き換え"""
    page = db.query(WikiPage).filter(WikiPage.id == page_id).first()
    if not page:
        raise NotFoundError(f"WikiPage {page_id} not found")

    tags = db.query(WikiTag).filter(WikiTag.id.in_(tag_ids)).all()
    page.tags = tags
    db.flush()
    return page


def get_pages_by_tag(db: Session, tag_slug: str) -> list:
    """タグスラッグでページを検索"""
    return (
        db.query(WikiPage)
        .join(wiki_page_tags, WikiPage.id == wiki_page_tags.c.page_id)
        .join(WikiTag, WikiTag.id == wiki_page_tags.c.tag_id)
        .filter(WikiTag.slug == tag_slug)
        .order_by(WikiPage.updated_at.desc())
        .all()
    )
```

### 5.3 Alembic マイグレーション

```python
# alembic/versions/xxxx_add_wiki_tags_categories.py
"""add wiki tags and categories

Revision ID: xxxx
Revises: (wiki_pages migration ID)
"""
from alembic import op
import sqlalchemy as sa


def upgrade() -> None:
    # wiki_categories
    op.create_table(
        "wiki_categories",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("description", sa.String(500), nullable=True),
        sa.Column("color", sa.String(7), nullable=False, server_default="#6c757d"),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("idx_wiki_categories_name", "wiki_categories", ["name"], unique=True)

    # wiki_tags
    op.create_table(
        "wiki_tags",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("slug", sa.String(100), nullable=False),
        sa.Column("color", sa.String(7), nullable=False, server_default="#6c757d"),
        sa.Column("created_by", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("idx_wiki_tags_name", "wiki_tags", ["name"], unique=True)
    op.create_index("idx_wiki_tags_slug", "wiki_tags", ["slug"], unique=True)

    # wiki_page_tags (中間テーブル)
    op.create_table(
        "wiki_page_tags",
        sa.Column("page_id", sa.Integer(), sa.ForeignKey("wiki_pages.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("tag_id",  sa.Integer(), sa.ForeignKey("wiki_tags.id",  ondelete="CASCADE"), primary_key=True),
    )
    op.create_index("idx_wiki_page_tags_tag_id", "wiki_page_tags", ["tag_id"])

    # wiki_pages に category_id カラムを追加
    op.add_column("wiki_pages", sa.Column(
        "category_id", sa.Integer(),
        sa.ForeignKey("wiki_categories.id", ondelete="SET NULL"),
        nullable=True,
    ))
    op.create_index("idx_wiki_pages_category_id", "wiki_pages", ["category_id"])


def downgrade() -> None:
    op.drop_index("idx_wiki_pages_category_id", "wiki_pages")
    op.drop_column("wiki_pages", "category_id")
    op.drop_table("wiki_page_tags")
    op.drop_table("wiki_tags")
    op.drop_table("wiki_categories")
```

---

## 6. フロントエンド

### 6.1 タグ入力（編集画面）

タグ名を入力するインクリメンタル検索付き入力フィールド。

```html
<!-- templates/wiki_edit.html のタグ入力エリア -->
<div class="mb-3">
  <label class="form-label fw-semibold">タグ</label>
  <div id="wiki-tag-input-area">
    <!-- 選択済みタグ（バッジ） -->
    <div id="wiki-selected-tags" class="d-flex flex-wrap gap-1 mb-2"></div>
    <!-- タグ検索入力 -->
    <div class="position-relative" style="max-width: 300px;">
      <input type="text" id="wiki-tag-search" class="form-control form-control-sm"
             placeholder="タグを入力して追加...">
      <div id="wiki-tag-suggestions" class="dropdown-menu w-100" style="max-height: 200px; overflow-y: auto;"></div>
    </div>
  </div>
</div>
```

```javascript
// static/js/wiki.js のタグ管理部分

let selectedTags = [];  // { id, name, slug, color }

// タグ検索（インクリメンタル）
document.getElementById("wiki-tag-search")?.addEventListener("input", async (e) => {
  const q = e.target.value.trim();
  const suggestions = document.getElementById("wiki-tag-suggestions");

  if (q.length < 1) {
    suggestions.classList.remove("show");
    return;
  }

  const res = await fetch(`/api/wiki/tags?q=${encodeURIComponent(q)}`);
  const tags = await res.json();

  // 未選択のタグのみ表示
  const unselected = tags.filter(t => !selectedTags.some(s => s.id === t.id));

  suggestions.innerHTML = [
    ...unselected.map(t => `
      <button class="dropdown-item" onclick="addTag(${t.id}, '${escapeHtml(t.name)}', '${t.slug}', '${t.color}')">
        <span class="badge me-1" style="background:${t.color}">${escapeHtml(t.name)}</span>
        <small class="text-muted">${t.page_count} ページ</small>
      </button>
    `),
    // 新規作成オプション（完全一致がない場合のみ）
    ...(unselected.length === 0 || !tags.some(t => t.name === q) ? [`
      <button class="dropdown-item text-primary" onclick="createAndAddTag('${escapeHtml(q)}')">
        <i class="bi bi-plus-circle me-1"></i>「${escapeHtml(q)}」を新規作成して追加
      </button>
    `] : []),
  ].join("");

  suggestions.classList.add("show");
});

function addTag(id, name, slug, color) {
  if (selectedTags.some(t => t.id === id)) return;
  selectedTags.push({ id, name, slug, color });
  renderSelectedTags();
  document.getElementById("wiki-tag-search").value = "";
  document.getElementById("wiki-tag-suggestions").classList.remove("show");
}

function removeTag(tagId) {
  selectedTags = selectedTags.filter(t => t.id !== tagId);
  renderSelectedTags();
}

function renderSelectedTags() {
  const container = document.getElementById("wiki-selected-tags");
  container.innerHTML = selectedTags.map(t => `
    <span class="badge d-inline-flex align-items-center gap-1" style="background:${t.color}">
      ${escapeHtml(t.name)}
      <button type="button" class="btn-close btn-close-white btn-sm"
              onclick="removeTag(${t.id})" style="font-size: 0.6em;"></button>
    </span>
  `).join("");
}

async function createAndAddTag(name) {
  const res = await fetch("/api/wiki/tags", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name }),
  });
  if (res.ok) {
    const tag = await res.json();
    addTag(tag.id, tag.name, tag.slug, tag.color);
  }
}
```

### 6.2 カテゴリ選択（編集画面）

```html
<!-- templates/wiki_edit.html のカテゴリ選択 -->
<div class="mb-3">
  <label class="form-label fw-semibold">カテゴリ</label>
  <select id="wiki-category-select" class="form-select form-select-sm" style="max-width: 200px;">
    <option value="">-- なし --</option>
    {% for cat in wiki_categories %}
    <option value="{{ cat.id }}"
      {% if page and page.category_id == cat.id %}selected{% endif %}>
      {{ cat.name }}
    </option>
    {% endfor %}
  </select>
</div>
```

### 6.3 タグフィルタ（一覧・サイドバー）

```html
<!-- templates/wiki.html サイドバーのタグクラウド -->
<div class="wiki-sidebar-section mt-3">
  <div class="fw-semibold small text-muted mb-2">タグ</div>
  <div class="d-flex flex-wrap gap-1">
    {% for tag in wiki_tags %}
    <a href="/wiki?tag={{ tag.slug }}"
       class="badge text-decoration-none {% if current_tag == tag.slug %}opacity-100{% else %}opacity-75{% endif %}"
       style="background: {{ tag.color }}">
      {{ tag.name }}
      <small>({{ tag.page_count }})</small>
    </a>
    {% endfor %}
  </div>
</div>

<!-- カテゴリフィルタ -->
<div class="wiki-sidebar-section mt-3">
  <div class="fw-semibold small text-muted mb-2">カテゴリ</div>
  <ul class="list-unstyled small">
    <li><a href="/wiki" class="text-decoration-none {% if not current_category %}fw-bold{% endif %}">すべて</a></li>
    {% for cat in wiki_categories %}
    <li>
      <a href="/wiki?category_id={{ cat.id }}"
         class="text-decoration-none {% if current_category == cat.id %}fw-bold{% endif %}">
        <span class="badge me-1" style="background:{{ cat.color }}; width: 8px; height: 8px; padding: 0;">&nbsp;</span>
        {{ cat.name }} ({{ cat.page_count }})
      </a>
    </li>
    {% endfor %}
  </ul>
</div>
```

---

## 7. 保存時の処理フロー

```
[フロントエンド]
  1. 「保存」ボタンクリック
  2. PUT /api/wiki/pages/{id}
     body: { title, content, visibility, category_id }
  3. PUT /api/wiki/pages/{id}/tags
     body: { tag_ids: [1, 3, 5] }

[バックエンド]
  1. WikiPage を更新（category_id 含む）
  2. wiki_page_tags を一括置き換え（DELETE + INSERT）
  3. 更新後の WikiPage（tags リレーション含む）を返却
```

> **最適化メモ:** タグ更新を `PUT /api/wiki/pages/{id}` に統合することも可能だが、
> タグ変更頻度はコンテンツ変更と異なるため分離する設計とした。

---

## 8. 認可ルール

| 操作 | 必要権限 |
|------|---------|
| カテゴリ閲覧 | 認証済みユーザー |
| カテゴリ作成・更新・削除 | admin のみ |
| タグ閲覧 | 認証済みユーザー |
| タグ作成 | 認証済みユーザー（全員） |
| タグ削除 | admin のみ |
| ページへのタグ付与・解除 | ページ作成者 or admin |
| ページへのカテゴリ設定 | ページ作成者 or admin |

---

## 9. テスト方針

### 9.1 テストケース（予定）

| # | テストケース | 確認内容 |
|---|------------|---------|
| 1 | カテゴリ作成 | 201 Created、admin のみ |
| 2 | カテゴリ名重複 | 400 Bad Request |
| 3 | 一般ユーザーのカテゴリ作成 | 403 Forbidden |
| 4 | カテゴリ削除時の wiki_pages | category_id が NULL になる（SET NULL） |
| 5 | タグ作成（一般ユーザー） | 201 Created（全ユーザー可） |
| 6 | タグ名重複 | 400 Bad Request |
| 7 | タグ一覧（部分一致フィルタ） | `?q=AP` で `API` が返る |
| 8 | ページへのタグ付与 | `PUT /api/wiki/pages/{id}/tags` で更新される |
| 9 | タグでページフィルタ | `?tag=api` で対象ページのみ返る |
| 10 | カテゴリでページフィルタ | `?category_id=1` で対象ページのみ返る |
| 11 | タグ削除 | wiki_page_tags も CASCADE 削除される |
| 12 | タグ削除（admin のみ） | 一般ユーザーは 403 Forbidden |
| 13 | ページ取得レスポンスに tags 含む | `tags` フィールドに WikiTagResponse[] が含まれる |

---

## 10. 技術的負債・今後の課題

| 項目 | 内容 | 優先度 |
|------|------|--------|
| タグのカラーピッカー | 現状はデフォルト色のみ。編集画面でカラーピッカーを追加 | 低 |
| タグの統合（マージ） | 類似タグを1つにまとめる admin 機能 | 低 |
| カテゴリのアイコン | `color` に加えて Bootstrap Icons クラス名を設定可能に | 低 |
| タグ検索の AND/OR 切替 | 現状は OR（いずれか1つ）。AND 条件（全て含む）にも対応 | 低 |
| 人気タグ | アクセス数・使用頻度でタグをソートする機能 | 低 |
