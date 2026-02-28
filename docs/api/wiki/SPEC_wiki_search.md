# WIKI 全文検索 設計書

> 本ドキュメントは [spec_wiki.md](../../spec_wiki.md) の補足資料です。
>
> フェーズ1: PostgreSQL FTS（Full Text Search）による WIKI ページ全文検索

---

## 1. 概要

### 1.1 採用技術

| 項目 | 内容 |
|------|------|
| 検索エンジン | **PostgreSQL FTS**（`tsvector` / `tsquery`） |
| 追加ライブラリ | なし（PostgreSQL 内蔵機能のみ） |
| インデックス | **GIN インデックス**（`tsvector` 型への高速全文検索） |
| 日本語対応 | `pg_catalog.simple` 辞書（基本対応） / `pg_bigm` 拡張（高精度、オプション） |
| キーワードハイライト | PostgreSQL `ts_headline()` 関数 |
| 関連度スコアリング | PostgreSQL `ts_rank()` 関数 |

### 1.2 設計方針

- **追加 DB 不要**: PostgreSQL の FTS を活用し、Elasticsearch 等の外部検索エンジンを不要にする
- **自動インデックス更新**: データベーストリガーで `search_vector` を自動更新する
- **タイトル重み付け**: タイトルの一致をコンテンツより高いウェイトで扱う
- **日本語の扱い**: フェーズ1は `simple` 辞書でスペース区切り検索。必要に応じて `pg_bigm` に移行可能

---

## 2. データモデル

### 2.1 search_vector カラム

`wiki_pages` テーブルの `search_vector` カラムを活用する（`SPEC_wiki_pages.md` 参照）。

```sql
-- wiki_pages.search_vector カラム（再掲）
search_vector TSVECTOR  -- GIN インデックス付き
```

### 2.2 インデックス設計

```sql
-- GIN インデックス（SPEC_wiki_pages.md のマイグレーションで作成済み）
CREATE INDEX idx_wiki_pages_search ON wiki_pages USING GIN(search_vector);
```

---

## 3. 全文検索インデックスの管理

### 3.1 search_vector の内容

タイトルとコンテンツのテキストを合成した `tsvector` を保存する。

**タイトルと本文のウェイト:**

| 対象 | ウェイト | 意味 |
|------|---------|------|
| `title` | `'A'`（最高） | タイトル一致は最も高いスコア |
| `content` テキスト | `'B'` | 本文の一致は次点スコア |

### 3.2 トリガー関数

`search_vector` をタイトルから自動更新するトリガー。本文（JSON）からのテキスト抽出は別途 Python 側で行い、`search_vector` を更新する。

```sql
-- マイグレーションで作成（フェーズ1: タイトルのみのシンプル実装）
CREATE TRIGGER wiki_pages_search_update
BEFORE INSERT OR UPDATE ON wiki_pages
FOR EACH ROW EXECUTE FUNCTION
tsvector_update_trigger(search_vector, 'pg_catalog.simple', title);
```

> **Note**: フェーズ1ではタイトルのみを全文検索対象とする。コンテンツ（Tiptap JSON）からのテキスト抽出はフェーズ2で追加する予定。JSON の中のテキストを `tsvector` に変換するには Python 側での前処理が必要なため。

### 3.3 コンテンツ更新時の search_vector 手動更新（将来）

Tiptap JSON からテキストを抽出して `search_vector` を更新する Python 関数:

```python
# app/crud/wiki_page.py

def extract_text_from_tiptap(content: dict) -> str:
    """Tiptap JSON からプレーンテキストを再帰的に抽出"""
    texts = []
    if isinstance(content, dict):
        if content.get("type") == "text" and content.get("text"):
            texts.append(content["text"])
        for child in content.get("content", []):
            texts.append(extract_text_from_tiptap(child))
    return " ".join(t for t in texts if t)


def update_search_vector(db, page_id: int, title: str, content: dict) -> None:
    """search_vector を手動更新（コンテンツ全文検索対応）"""
    body_text = extract_text_from_tiptap(content)
    db.execute(
        text("""
            UPDATE wiki_pages
            SET search_vector =
                setweight(to_tsvector('pg_catalog.simple', :title), 'A') ||
                setweight(to_tsvector('pg_catalog.simple', :body), 'B')
            WHERE id = :page_id
        """),
        {"title": title, "body": body_text, "page_id": page_id},
    )
```

---

## 4. 検索 API

### 4.1 エンドポイント

| メソッド | パス | 説明 | 認証 |
|---------|------|------|------|
| GET | `/api/wiki/search` | WIKI 全文検索 | 必要 |

### 4.2 GET /api/wiki/search

クエリ文字列で WIKI ページを全文検索する。

- **クエリパラメータ:**

| パラメータ | 型 | デフォルト | 説明 |
|------------|-----|-----------|------|
| q | string | 必須 | 検索キーワード |
| limit | integer | 20 | 最大返却件数（上限 100） |
| offset | integer | 0 | ページングオフセット |

- **レスポンス:** `200 OK` - `WikiSearchResponse`
- **エラー:** `422 Unprocessable Entity` - `q` が空文字

**レスポンス例:**

```json
{
  "query": "API 設計",
  "total": 3,
  "results": [
    {
      "id": 2,
      "title": "API 設計ガイド",
      "slug": "dev-api-design",
      "headline": "...この <b>API</b> <b>設計</b>ガイドでは REST の原則...",
      "author_name": "田中 太郎",
      "updated_at": "2026-02-25T10:00:00+09:00",
      "rank": 0.0759906
    }
  ]
}
```

### 4.3 検索 CRUD 実装

```python
# app/crud/wiki_page.py

from sqlalchemy import func, text
from app.models.wiki_page import WikiPage


def search_pages(db, query: str, limit: int = 20, offset: int = 0) -> dict:
    """全文検索。タイトルウェイト A > コンテンツウェイト B でスコアリング"""
    ts_query = func.plainto_tsquery("pg_catalog.simple", query)

    # 検索実行
    results = (
        db.query(WikiPage)
        .filter(WikiPage.search_vector.op("@@")(ts_query))
        .order_by(
            func.ts_rank(WikiPage.search_vector, ts_query).desc()
        )
        .offset(offset)
        .limit(limit)
        .all()
    )

    # 総件数
    total = (
        db.query(func.count(WikiPage.id))
        .filter(WikiPage.search_vector.op("@@")(ts_query))
        .scalar()
    )

    # ハイライト生成（タイトルを優先）
    def get_headline(page: WikiPage) -> str:
        row = db.execute(
            text("""
                SELECT ts_headline(
                    'pg_catalog.simple',
                    :title,
                    plainto_tsquery('pg_catalog.simple', :query),
                    'MaxFragments=1, MaxWords=20, MinWords=5, StartSel=<b>, StopSel=</b>'
                )
            """),
            {"title": page.title, "query": query},
        ).fetchone()
        return row[0] if row else page.title

    return {
        "query": query,
        "total": total,
        "results": [
            {
                "id": p.id,
                "title": p.title,
                "slug": p.slug,
                "headline": get_headline(p),
                "author_id": p.author_id,
                "updated_at": p.updated_at,
            }
            for p in results
        ],
    }
```

### 4.4 スキーマ

```python
# app/schemas/wiki_page.py の追加

from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class WikiSearchResult(BaseModel):
    id: int
    title: str
    slug: str
    headline: str            # ts_headline() で生成したスニペット（HTMLタグ含む）
    author_id: Optional[int]
    author_name: Optional[str]
    updated_at: Optional[datetime]
    rank: float


class WikiSearchResponse(BaseModel):
    query: str
    total: int
    results: list[WikiSearchResult]
```

---

## 5. フロントエンド: 検索 UI

### 5.1 検索バー（サイドバー / ヘッダー）

```html
<!-- templates/wiki.html 内の検索フォーム -->
<form id="wiki-search-form" class="mb-3">
  <div class="input-group input-group-sm">
    <input type="text" id="wiki-search-input" class="form-control"
           placeholder="WIKI 内を検索..." autocomplete="off">
    <button type="submit" class="btn btn-outline-secondary">
      <i class="bi bi-search"></i>
    </button>
  </div>
</form>
```

### 5.2 インクリメンタル検索（デバウンス）

```javascript
// static/js/wiki.js

let searchTimeout = null;

document.getElementById("wiki-search-input")?.addEventListener("input", (e) => {
  clearTimeout(searchTimeout);
  const q = e.target.value.trim();
  if (q.length < 2) {
    hideSearchResults();
    return;
  }
  // 300ms デバウンス
  searchTimeout = setTimeout(() => performSearch(q), 300);
});

async function performSearch(query) {
  const res = await fetch(`/api/wiki/search?q=${encodeURIComponent(query)}&limit=10`);
  if (!res.ok) return;
  const data = await res.json();
  renderSearchResults(data);
}

function renderSearchResults(data) {
  const container = document.getElementById("wiki-search-results");
  if (!container) return;

  if (data.results.length === 0) {
    container.innerHTML = `<div class="p-2 text-muted small">「${escapeHtml(data.query)}」に一致するページはありません</div>`;
    container.classList.remove("d-none");
    return;
  }

  container.innerHTML = data.results.map(r => `
    <a href="/wiki/${r.slug}" class="list-group-item list-group-item-action py-2">
      <div class="fw-semibold">${escapeHtml(r.title)}</div>
      <div class="text-muted small">${r.headline}</div>
      <div class="text-muted small">${r.updated_at ? formatDate(r.updated_at) : ""}</div>
    </a>
  `).join("");
  container.classList.remove("d-none");
}

function hideSearchResults() {
  const container = document.getElementById("wiki-search-results");
  if (container) container.classList.add("d-none");
}
```

### 5.3 検索結果ページ（/wiki/search）

クエリパラメータ `?q=xxx` を持つ専用ページ。

```html
<!-- templates/wiki.html の検索結果エリア -->
{% if search_results %}
<div class="wiki-search-results">
  <h5>「{{ search_query }}」の検索結果（{{ search_results.total }} 件）</h5>
  {% for result in search_results.results %}
  <div class="card mb-2">
    <div class="card-body py-2">
      <a href="/wiki/{{ result.slug }}" class="fw-semibold text-decoration-none">
        {{ result.title }}
      </a>
      <div class="text-muted small mt-1">{{ result.headline | safe }}</div>
      <div class="text-muted small">{{ result.updated_at | datetime }}</div>
    </div>
  </div>
  {% endfor %}
</div>
{% endif %}
```

---

## 6. 日本語検索の改善（オプション）

### 6.1 現状の制限

`pg_catalog.simple` 辞書はスペース区切りによるトークン化のみ行う。日本語は文字間にスペースがないため、単語分割が不正確になる。

**例:**
- 検索クエリ: `API設計`
- インデックス: `API設計` → `api設計` 1トークン
- → `設計` だけで検索しても一致しない場合がある

### 6.2 pg_bigm による改善

`pg_bigm` 拡張を追加すると、バイグラム（2文字 N-gram）で全文インデックスを作成し、日本語の部分一致検索の精度が向上する。

```sql
-- PostgreSQL に pg_bigm 拡張を追加
CREATE EXTENSION IF NOT EXISTS pg_bigm;

-- バイグラム GIN インデックスを作成
CREATE INDEX idx_wiki_pages_bigm_title ON wiki_pages USING GIN(title gin_bigm_ops);
CREATE INDEX idx_wiki_pages_bigm_content ON wiki_pages USING GIN(content::text gin_bigm_ops);
```

```python
# pg_bigm を使用した検索クエリ
def search_pages_bigm(db, query: str, limit: int = 20) -> list:
    return (
        db.query(WikiPage)
        .filter(WikiPage.title.op("%")(query))  # pg_bigm の LIKE 演算子
        .order_by(WikiPage.similarity.desc())    # pg_bigm の類似度スコア
        .limit(limit)
        .all()
    )
```

> **フェーズ1での方針:** `pg_catalog.simple` でスタートし、日本語検索精度の改善が必要になった時点で `pg_bigm` へ移行する。マイグレーションで後から追加できるため、初期実装への影響はない。

---

## 7. ページルーター（バックエンド）

```python
# app/routers/api_wiki.py（検索エンドポイント部分）

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from portal_core.database import get_db
from portal_core.core.deps import get_current_user_id
from app.crud.wiki_page import search_pages
from app.schemas.wiki_page import WikiSearchResponse

router = APIRouter(prefix="/api/wiki", tags=["wiki"])


@router.get("/search", response_model=WikiSearchResponse)
def search_wiki(
    q: str = Query(..., min_length=1, max_length=200),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    _user_id: int = Depends(get_current_user_id),
):
    """WIKI ページの全文検索"""
    result = search_pages(db, q, limit=limit, offset=offset)
    return result
```

---

## 8. テスト方針

### 8.1 テストケース（予定）

| # | テストケース | 確認内容 |
|---|------------|---------|
| 1 | タイトル検索（完全一致） | タイトルに含まれるキーワードで検索結果が返る |
| 2 | タイトル検索（部分一致） | 複数単語の一部で検索しても返る |
| 3 | 空クエリ | 422 エラーが返る |
| 4 | 検索結果なし | `total: 0, results: []` が返る |
| 5 | ページング | `offset` と `limit` が正しく機能する |
| 6 | ランキング | タイトル完全一致のページが上位に来る |
| 7 | ハイライト | `headline` にキーワードが `<b>` タグで含まれる |
| 8 | private ページ | 非作成者の検索結果に含まれない |
| 9 | search_vector 更新 | ページ更新後に新キーワードで検索できる |
| 10 | 未認証アクセス | 401 Unauthorized が返る |

### 8.2 テストコード（例）

```python
# tests/test_wiki.py（検索テスト部分）

def test_search_returns_result(client, db_session):
    """タイトルに含まれるキーワードで検索結果が返ること"""
    # ページ作成
    res = client.post("/api/wiki/pages", json={
        "title": "API 設計ガイド",
        "content": {"type": "doc", "content": []},
    })
    assert res.status_code == 201

    # search_vector の更新を待つ（トリガーが発火するよう flush）
    db_session.flush()

    # 検索
    res = client.get("/api/wiki/search?q=API")
    assert res.status_code == 200
    data = res.json()
    assert data["total"] >= 1
    assert any(r["title"] == "API 設計ガイド" for r in data["results"])


def test_search_empty_query_returns_422(client):
    """空クエリで 422 エラーが返ること"""
    res = client.get("/api/wiki/search?q=")
    assert res.status_code == 422


def test_search_no_results(client, db_session):
    """ヒットしないキーワードで空の結果が返ること"""
    res = client.get("/api/wiki/search?q=存在しないキーワード12345")
    assert res.status_code == 200
    data = res.json()
    assert data["total"] == 0
    assert data["results"] == []
```

---

## 9. 技術的負債・今後の課題

| 項目 | 内容 | 優先度 |
|------|------|--------|
| コンテンツ全文検索 | フェーズ1はタイトルのみ。本文の Tiptap JSON からテキスト抽出してインデックスに追加する | 中（フェーズ2） |
| 日本語検索精度 | `pg_bigm` 拡張の追加（バイグラム N-gram による部分一致精度向上） | 低 |
| 検索候補サジェスト | インクリメンタル検索のドロップダウン UI 精度向上 | 低 |
| 高度な検索オプション | フィルタ（visibility、作成者、更新日時範囲）の追加 | 低 |
| 検索ログ | 検索キーワードの集計・人気コンテンツ分析 | 低 |
