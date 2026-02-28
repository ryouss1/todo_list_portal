# Wiki画面 (`/wiki`, `/wiki/new`, `/wiki/{slug}`, `/wiki/{slug}/edit`)

> 本ドキュメントは [spec_function.md](../spec_function.md) から分割された画面仕様です。

## 画面一覧

| パス | 説明 |
|------|------|
| `/wiki` | Wiki一覧（階層ツリー + ページ一覧） |
| `/wiki/new` | 新規ページ作成 |
| `/wiki/{slug}` | ページ閲覧 |
| `/wiki/{slug}/edit` | ページ編集 |

---

## Wiki一覧画面 (`/wiki`)

### 表示機能

- 左サイドバー: 階層ツリー表示（`GET /api/wiki/pages/tree`）
  - 親ページ・子ページを入れ子リストで表示
  - ページクリックで `/wiki/{slug}` に遷移
- メインエリア: ページ一覧テーブル
  - タイトル、カテゴリ（色付きバッジ）、タグ（色付きバッジ）、公開範囲、作成者、更新日時
- フィルタ: カテゴリIDフィルタ、タグスラッグフィルタ（URLクエリパラメータ対応）
- 公開範囲バッジ: `local`（自部署）/ `public`（全員）/ `private`（非公開）

### 操作機能

- **新規作成ボタン**: `/wiki/new` に遷移
- **ページクリック**: ページ閲覧画面に遷移
- タグクリックでタグフィルタを適用

---

## 新規ページ作成画面 (`/wiki/new`)

### 操作機能

- **タイトル入力**: テキストフィールド
- **スラッグ**: タイトルから自動生成（手動編集可）
- **親ページ選択**: ドロップダウン（階層構造の設定）
- **カテゴリ選択**: ドロップダウン（admin が作成したカテゴリ一覧）
- **タグ選択**: タグ名検索によるマルチセレクト
- **公開範囲選択**: `local`（デフォルト）/ `public` / `private`
- **本文エディタ**: Toast UI Editor（WYSIWYGまたはMarkdownモード切り替え可）
- **保存ボタン**: `POST /api/wiki/pages/` で作成 → ページ閲覧画面に遷移

---

## ページ閲覧画面 (`/wiki/{slug}`)

### 表示機能

- **パンくずナビ**: ルートからの階層パスを表示（`WikiPageDetailResponse.breadcrumbs`）
- **ページタイトル**: H1 表示
- **メタ情報**: カテゴリ（色付きバッジ）、タグ（色付きバッジ）、公開範囲、作成者、作成日時・更新日時
- **本文**: Toast UI Editor の Viewer モードで Markdown をレンダリング
- **タスクリンク**: ページに紐づくタスクリストアイテム・進行中タスクをセクション表示（`GET /api/wiki/pages/{id}/tasks`）
  - タスクリストアイテム: タイトル、ステータス、担当者、予定日、Backlogチケット番号
  - 進行中タスク: タスクタイトル（スナップショット）、ステータス、作成者、Backlogチケット番号
- **子ページ一覧**: 直下の子ページをリスト表示

### 操作機能

- **編集ボタン**: 作成者のみ表示 → `/wiki/{slug}/edit` に遷移
- **削除ボタン**: 作成者のみ表示 → 確認ダイアログ後に `DELETE /api/wiki/pages/{id}`
- **タグクリック**: タグフィルタ付きの Wiki 一覧に遷移（`/wiki?tag_slug=...`）

---

## ページ編集画面 (`/wiki/{slug}/edit`)

### 操作機能

- **タイトル編集**: テキストフィールド
- **スラッグ編集**: テキストフィールド
- **親ページ変更**: ドロップダウン（循環参照チェック付き）→ `PUT /api/wiki/pages/{id}/move`
- **カテゴリ変更**: ドロップダウン
- **タグ変更**: タグ名検索によるマルチセレクト → `PUT /api/wiki/pages/{id}/tags`
- **公開範囲変更**: セレクト
- **本文エディタ**: Toast UI Editor
- **タスクリストアイテムリンク**: 検索・選択 → `PUT /api/wiki/pages/{id}/tasks/task-items`
- **保存ボタン**: `PUT /api/wiki/pages/{id}` で更新 → ページ閲覧画面に遷移
- **キャンセル**: ページ閲覧画面に戻る

---

## 公開範囲（visibility）

| 値 | 表示名 | 閲覧できるユーザー |
|----|-------|-----------------|
| `local` | 自部署 | 同一グループのユーザー（デフォルト） |
| `public` | 全員 | 全ログインユーザー |
| `private` | 非公開 | 作成者のみ |

---

## ファイルマッピング

| 項目 | ファイル |
|------|---------|
| テンプレート（一覧） | `templates/wiki.html` |
| テンプレート（閲覧） | `templates/wiki_page.html` |
| テンプレート（編集・新規作成） | `templates/wiki_edit.html` |
| JavaScript | `static/js/wiki.js` |
| ルーター（ページ） | `app/routers/pages.py` |
| API ルーター | `app/routers/api_wiki.py` |
| サービス | `app/services/wiki_service.py` |
| CRUD | `app/crud/wiki_page.py`, `app/crud/wiki_tag.py`, `app/crud/wiki_task_link.py` |
| モデル | `app/models/wiki_page.py`, `app/models/wiki_category.py`, `app/models/wiki_tag.py`, `app/models/wiki_attachment.py` |
