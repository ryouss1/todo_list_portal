# ISSUE1: WIKI 機能設計 課題一覧

> 作成日: 2026-02-25
> 関連設計書: [spec_wiki.md](./spec_wiki.md)

---

## 概要

WIKI 機能の設計レビューで発見された課題・技術的リスク・未解決事項をまとめる。

---

## 課題一覧

### ISSUE-1-01: ~~tasks テーブルの物理削除による紐づき消失~~ → ✅ 解決済み

**解決日:** 2026-02-25
**解決方法:** `wiki_page_tasks` の設計を `ON DELETE CASCADE` → `ON DELETE SET NULL` + `task_title` スナップショット方式に変更。タスク完了後も紐づけレコードを保持し、UI では「完了済み」バッジ付きで表示する。

---

### ISSUE-1-02: ~~task_list_items 検索に `q` パラメータが未実装~~ → ✅ 解決済み

**解決日:** 2026-02-25
**解決方法:** `GET /api/task-list/all` に `q` クエリパラメータ（タイトル部分一致 ILIKE 検索）を追加。
**関連ファイル:**
- `app/crud/task_list_item.py`（`get_all_items()` に `q` 引数 + `ilike` フィルタ追加）
- `app/services/task_list_service.py`（`list_all()` に `q` 引数追加）
- `app/routers/api_task_list.py`（`GET /all` に `q: Optional[str] = Query(None)` 追加）
- `tests/test_task_list.py`（`test_all_q_filter_*` 3件追加）

---

### ISSUE-1-03: ~~添付ファイルの孤立（物理ファイル残存）~~ → ✅ 解決済み

**解決日:** 2026-02-25
**解決方法（対策1）:** `app/models/wiki_attachment.py` に `WikiAttachment` モデルを新規作成し、SQLAlchemy `@event.listens_for(WikiAttachment, "after_delete")` イベントリスナーを実装。レコード削除時（直接削除・CASCADE 削除いずれも）に `stored_path` の物理ファイルを自動削除する。`WikiPage.attachments` に `cascade="all, delete-orphan"` を設定済み。
**関連ファイル:**
- `app/models/wiki_attachment.py`（新規作成）
- `app/models/wiki_page.py`（`attachments` リレーション追加）
- `app/models/__init__.py`（`WikiAttachment` 登録）
- `alembic/versions/d4e5f6a7b8c9_add_wiki_attachments.py`（マイグレーション新規作成）

---

### ISSUE-1-04: 添付ファイルの MIME タイプ検証が不十分

**発見箇所:** [SPEC_wiki_attachments.md](./api/wiki/SPEC_wiki_attachments.md) セクション 11
**優先度:** 中
**状態:** 未解決

**内容:**
アップロード時の `file.content_type` はクライアントが送信するヘッダーであり、偽装が可能。許可拡張子チェックのみでは、`.txt` に偽装した実行ファイルなどを受け入れてしまうリスクがある。

**影響範囲:** セキュリティ（ファイルアップロード安全性）

**対策案:**
- `python-magic`（libmagic バインディング）でファイルマジックバイト（先頭バイト列）を検証する
- Phase 2 では拡張子チェック + コンテンツタイプの大まかな整合チェック（画像拡張子なら `image/*` であることを確認）
- Phase 3 で `python-magic` による厳密なチェックを追加

**推奨:** Phase 2 では許可拡張子 + 基本的な content_type チェック。Phase 3 で `python-magic` 導入。

---

### ISSUE-1-05: 大ファイルのメモリ問題（全量 read）

**発見箇所:** [SPEC_wiki_attachments.md](./api/wiki/SPEC_wiki_attachments.md) セクション 11
**優先度:** 中
**状態:** 未解決

**内容:**
現在の設計では `content = await file.read()` で全ファイルをメモリに読み込んでからサイズチェックしている。50MB のファイルを複数同時アップロードするとメモリ消費が増大する。

**影響範囲:** サーバーメモリ消費（高負荷時）

**対策案:**
- `SpooledTemporaryFile` または `UploadFile.file` を使ったストリーミング書き込み
- `Content-Length` ヘッダーの事前チェック（ただし信頼性は低い）
- FastAPI の `max_upload_size` ミドルウェア設定でリクエストサイズを制限する

**推奨:** Phase 2 では `MAX_UPLOAD_SIZE` ミドルウェア設定で対応。Phase 3 でストリーミング書き込みに変更。

---

### ISSUE-1-06: ~~`public` ページの未認証アクセス制御~~ → ✅ 解決済み

**解決日:** 2026-02-25
**解決方法（推奨案）:**
1. `portal_core/portal_core/core/deps.py` に `get_optional_user_id()` を追加。未認証時は `None` を返し 401 を発生させない。
2. `app/core/deps.py` の shim にも `get_optional_user_id` を追加（後方互換）。
3. `main.py` に `portal.register_public_prefix("/wiki")` を追加し、認証ミドルウェアによる `/wiki*` への `/login` リダイレクトを抑制。
4. `app/routers/api_wiki.py` の `get_page_by_slug` / `get_page` エンドポイントを `get_current_user_id` → `get_optional_user_id` に変更。
5. アクセス制御はサービス層の `_check_visibility()` が担当（`public` は全員閲覧可、`internal`/`private` は未認証時 403）。
**関連ファイル:**
- `portal_core/portal_core/core/deps.py`（`get_optional_user_id` 追加）
- `app/core/deps.py`（shim に追加）
- `main.py`（`/wiki` 公開パス登録）
- `app/routers/api_wiki.py`（page view エンドポイントの依存関係変更）

---

### ISSUE-1-07: ~~wiki_pages のマイグレーション順序依存~~ → ✅ 解決済み

**解決日:** 2026-02-25
**解決方法:** マイグレーションファイルは既に正しい依存関係で分割・設定されていることを確認した。

**実際のマイグレーションチェーン（検証済み）:**
```
b3df810d3406 (add_site_links)
  ↓
a1c2d3e4f5b6 (add_wiki_pages)
  - upgrade() 内で wiki_categories → wiki_tags → wiki_pages → wiki_page_tags の順で作成
  - wiki_categories が wiki_pages より前に作成されるため FK 制約エラーなし
  ↓
b2c3d4e5f6a7 (add_wiki_task_links)
  - wiki_pages, task_list_items, tasks が存在した後に適用
  - wiki_page_task_items, wiki_page_tasks を作成
  ↓
c3d4e5f6a7b8 (wiki_content_to_markdown)
  ↓
d4e5f6a7b8c9 (add_wiki_attachments)
  - wiki_pages が存在した後に適用
  - wiki_attachments を作成
```

全マイグレーションの `down_revision` が正しく設定されており、FK 依存関係はすべて満たされている。

---

### ISSUE-1-08: Tiptap コンテンツ全文検索トリガーがタイトルのみ対象

**発見箇所:** [SPEC_wiki_pages.md](./api/wiki/SPEC_wiki_pages.md) セクション 9.1
**優先度:** 低
**状態:** 未解決（設計上の制約）

**内容:**
現在の全文検索トリガー (`tsvector_update_trigger`) はタイトルカラムのみを対象としている。本文（`content` カラム: Tiptap JSON）は検索対象外になっている。

詳細は [SPEC_wiki_search.md](./api/wiki/SPEC_wiki_search.md) に記載されているが、Tiptap JSON からテキストを抽出してトリガーで更新する方式はネイティブ PostgreSQL トリガーで実装困難なため、アプリ側の `update_search_vector()` 関数で対応する設計になっている。

**影響範囲:** 全文検索の本文ヒット精度

**対策:** SPEC_wiki_search.md の設計通り、ページ保存 API (`PUT /api/wiki/pages/{id}`) で `update_search_vector()` を呼び出す実装で対応。実装フェーズで確認。

---

### ISSUE-1-09: タグ逆引き機能（タスクリストアイテムからの WIKI 参照）が未実装

**発見箇所:** [SPEC_wiki_task_links.md](./api/wiki/SPEC_wiki_task_links.md) セクション 10
**優先度:** 低
**状態:** 設計なし

**内容:**
タスクリストアイテム詳細画面から「このタスクに紐づいている WIKI ページ」を参照する逆引き機能が未設計。

**影響範囲:** タスクリストアイテム詳細 UI（将来機能）

**対策案:**
- `GET /api/wiki/task-items/{task_item_id}/pages` エンドポイントを追加（Phase 2 以降）
- タスクリストアイテム詳細モーダルに「関連 WIKI」セクションを追加

---

### ISSUE-1-10: ~~`yjs_state` カラムのデータサイズ管理~~ → ✅ 解決済み（カラム削除）

**解決日:** 2026-02-27
**解決方法:** マイグレーション `c3d4e5f6a7b8`（`wiki_content_to_markdown`）で `wiki_pages.yjs_state` カラムを削除。Tiptap JSON から Markdown 形式への移行に際し、Yjs CRDT による共同編集アーキテクチャ（フェーズ3）を採用しない判断となったためカラム自体が不要になった。サイズ管理問題は対象のカラム自体がなくなったことで自動的に解消。

---

## 対応優先度まとめ

| ID | タイトル | 優先度 | 対応フェーズ |
|----|---------|--------|------------|
| ~~ISSUE-1-03~~ | ~~添付ファイルの孤立（物理ファイル残存）~~ | ~~高~~ | ✅ Phase 2 実装前に解決済み |
| ~~ISSUE-1-07~~ | ~~マイグレーション順序依存~~ | ~~高~~ | ✅ 実装時に正しく設定済みと確認 |
| ~~ISSUE-1-01~~ | ~~tasks 物理削除による紐づき消失~~ | ~~中~~ | ✅ 設計変更で解決済み |
| ~~ISSUE-1-02~~ | ~~task-list API に `q` パラメータ未実装~~ | ~~中~~ | ✅ `GET /api/task-list/all?q=` として実装済み |
| ISSUE-1-04 | MIME タイプ検証不十分 | 中 | Phase 2 実装時 |
| ISSUE-1-05 | 大ファイルのメモリ問題 | 中 | Phase 2 実装時 |
| ~~ISSUE-1-06~~ | ~~`public` ページの未認証アクセス制御~~ | ~~中~~ | ✅ Phase 1 実装中に解決済み |
| ISSUE-1-08 | 全文検索が本文非対象（トリガー制約） | 低 | Phase 1 実装中（設計通り） |
| ISSUE-1-09 | タスク逆引き機能未実装 | 低 | Phase 2 以降 |
| ~~ISSUE-1-10~~ | ~~yjs_state サイズ管理~~ | ~~低~~ | ✅ カラム削除済み（`c3d4e5f6a7b8`） |
