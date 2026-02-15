# Task List 機能仕様書

> タスクリスト（バックログ）管理機能の完全な仕様。アイテムの作成・割り当て・タスク変換・時間蓄積を含む。

---

## 1. 概要

### 1.1 背景

既存の Tasks ページは「作業中のタスクをタイマーで管理する」ための画面であり、
未来のタスクを含むバックログ管理や、担当者割り当て、サブタスクの機能がなかった。
Task List はこれらのギャップを埋めるバックログ管理機能として導入された。

Todo / Public Todos は Task List で代替されるため、ナビバーから非表示にしている
（コードは残存し、URL による直接アクセスは可能）。

### 1.2 目的

Task List 機能はチーム共有のバックログ（作業予定リスト）を管理する。
未割当アイテムはプールとして全員に公開され、自分にアサインして作業を開始できる。
「Start」操作でアイテムを Task（タイマー付き）にコピーし、作業時間を計測。
タスク完了時に蓄積された作業時間はソースアイテムに還元される。

### 1.3 データフロー

```
TaskListItem (バックログ) → [Start] → Task (タイマー管理) → [Done] → 時間を TaskListItem に蓄積
        ↑ 同一アイテムにリンクされた Task がなければ再 Start 可能  ↓
        └──────────── status を open に自動リセット ◄────────────┘
                     （リンクされた Task が全て完了した場合）
```

- Start は Mine タブからのみ実行可能
- **同一アイテムの重複制限**: 同じ TaskListItem からリンクされた Task（`source_item_id`）が既に存在する場合、再 Start はブロックされる（`400`）
- Stop / タイマー停止は Tasks 画面で行う（TaskList に Stop ボタンはない）
- Tasks で Done すると、TaskListItem のステータスと蓄積時間が自動更新される

---

## 2. データモデル

### 2.1 task_list_items テーブル

| カラム | 型 | 制約 | 説明 |
|--------|------|------|------|
| id | INTEGER | PK, AUTO INCREMENT | アイテムID |
| title | VARCHAR(500) | NOT NULL | アイテムタイトル |
| description | TEXT | NULL 可 | 詳細説明 |
| scheduled_date | DATE | NULL 可 | 予定日 |
| assignee_id | INTEGER | FK → users.id, NULL 可 | 担当ユーザー（NULL = 未割当） |
| created_by | INTEGER | FK → users.id, NOT NULL | 作成者 |
| status | VARCHAR(20) | DEFAULT "open", NOT NULL | ステータス（`open` / `in_progress` / `done`） |
| total_seconds | INTEGER | DEFAULT 0, NOT NULL | 蓄積作業時間（秒） |
| category_id | INTEGER | FK → task_categories.id, NULL 可 | タスク分類ID |
| backlog_ticket_id | VARCHAR(50) | NULL 可 | Backlogチケット番号（例: WHT-488） |
| created_at | DATETIME(TZ) | server_default=now() | 作成日時 |
| updated_at | DATETIME(TZ) | server_default=now(), onupdate=now() | 更新日時 |

### 2.2 tasks テーブルとの連携

| カラム | 型 | 制約 | 説明 |
|--------|------|------|------|
| source_item_id | INTEGER | FK → task_list_items.id (SET NULL), NULL 可 | コピー元の TaskListItem ID |

`tasks.source_item_id` は Start 操作で自動設定される。
TaskListItem が削除されても Task 側は `SET NULL` で残存する。

---

## 3. ステータス遷移

```
open ──[Start]──▶ in_progress
  │                    │
  │                    ├──[Tasks で全 Task Done]──▶ open（自動リセット）
  │                    │
  └──[Done(手動)]──────┘──▶ done
```

- **open**: 初期状態。未着手のアイテム。リンクされた Task がすべて完了すると自動的に戻る
- **in_progress**: Start 操作で Task にコピーされた状態。リンク中の Task がある限りこの状態
- **done**: 手動でステータスを done に変更。完了状態（自動リセットの対象外）

同一アイテムから既にリンクされた Task が存在する場合、再 Start はブロックされる（`400 ConflictError`）。
Task が Done / 削除されてリンクがなくなれば、再度 Start 可能。

### 3.1 ステータス自動同期

Tasks 画面で Task を Done（単一 / Batch-Done）した際、リンク元の TaskListItem のステータスを自動更新する。

| 条件 | 動作 |
|------|------|
| リンクされた Task が **全て完了**（残り 0 件） | `in_progress` → `open` に自動リセット |
| リンクされた Task が **まだ残っている** | `in_progress` のまま変化なし |
| TaskListItem が `done` の場合 | 変更しない（手動で done にしたものを勝手に戻さない） |

TaskList 画面に Stop ボタンはない。タイマー停止は Tasks 画面で行い、結果が TaskList に反映される。

---

## 4. API エンドポイント

認証: 全エンドポイントで必要（`Depends(get_current_user_id)`）
権限: アクセス制御はセクション 7 の可視性・編集権限ルールに準拠

### 4.1 一覧取得

| メソッド | パス | 説明 | レスポンス |
|---------|------|------|-----------|
| GET | `/api/task-list/all` | 全アイテム一覧（フィルター対応） | `200` TaskListItemResponse[] |
| GET | `/api/task-list/unassigned` | 未割当アイテム一覧 | `200` TaskListItemResponse[] |
| GET | `/api/task-list/mine` | 自分に割り当てられたアイテム一覧 | `200` TaskListItemResponse[] |

**`GET /all` クエリパラメータ**:
- `assignee_id` (任意): 指定時 → そのユーザーのアイテムのみ。`0` → 未割当のみ。省略 → 全件

ソート順: `scheduled_date ASC NULLS LAST` → `created_at ASC`

### 4.2 CRUD

| メソッド | パス | 説明 | レスポンス |
|---------|------|------|-----------|
| POST | `/api/task-list/` | アイテム作成 | `201` TaskListItemResponse |
| GET | `/api/task-list/{id}` | アイテム取得 | `200` TaskListItemResponse / `404` |
| PUT | `/api/task-list/{id}` | アイテム更新 | `200` TaskListItemResponse / `404` |
| DELETE | `/api/task-list/{id}` | アイテム削除 | `204` / `404` |

### 4.3 アサイン

| メソッド | パス | 説明 | レスポンス |
|---------|------|------|-----------|
| POST | `/api/task-list/{id}/assign` | 自分にアサイン | `200` TaskListItemResponse / `403` 他ユーザーにアサイン済 / `404` |
| POST | `/api/task-list/{id}/unassign` | アサイン解除 | `200` TaskListItemResponse / `403` in_progress時不可 / `404` |

### 4.4 Start（タスク変換）

| メソッド | パス | 説明 | レスポンス |
|---------|------|------|-----------|
| POST | `/api/task-list/{id}/start` | アイテムを Task にコピーして開始 | `200` TaskResponse / `400` 重複 / `403` 担当者でない / `404` |

Start 処理の流れ:
1. アイテムの存在チェック
2. **担当者チェック**: `assignee_id` が現在のユーザーであることを確認（`403`）
3. **重複チェック**: 同一 `source_item_id` を持つ Task が既に存在しないことを確認（`400 ConflictError`）
4. 新しい Task を作成（フィールドをコピー）
   - `title`, `description`, `category_id`, `backlog_ticket_id` → Task にコピー
   - `source_item_id` → アイテムの `id` を設定
   - `user_id` → 現在のユーザー
5. アイテムの `status` を `in_progress` に更新
6. TaskResponse を返却

---

## 5. スキーマ

### TaskListItemCreate
```json
{
  "title": "string (必須)",
  "description": "string (任意)",
  "scheduled_date": "date (任意)",
  "category_id": "int (任意)",
  "backlog_ticket_id": "string (任意)",
  "assignee_id": "int (任意)"
}
```

### TaskListItemUpdate
```json
{
  "title": "string (任意)",
  "description": "string (任意)",
  "scheduled_date": "date (任意)",
  "category_id": "int (任意)",
  "backlog_ticket_id": "string (任意)",
  "status": "open | in_progress | done (任意)"
}
```

### TaskListItemResponse
```json
{
  "id": 1,
  "title": "string",
  "description": "string|null",
  "scheduled_date": "date|null",
  "assignee_id": "int|null",
  "created_by": 1,
  "status": "open|in_progress|done",
  "total_seconds": 0,
  "category_id": "int|null",
  "backlog_ticket_id": "string|null",
  "created_at": "datetime",
  "updated_at": "datetime|null",
}
```

---

## 6. フロントエンド

### 6.1 画面構成（`/task-list`）

- テンプレート: `templates/task_list.html`
- JavaScript: `static/js/task_list.js`
- ナビバー: `bi-card-list` アイコンで表示（Todo / Public Todos は `d-none` で非表示）

```
Task List ページ
├── [自分 (Mine)] タブ ← デフォルト
│   └── テーブル一覧（自分にアサインされたアイテムのみ）
└── [全体 (All)] タブ
    ├── ユーザーフィルター（ドロップダウン: 全員 / 未割当 / ユーザー名）
    └── テーブル一覧（全アイテム表示）
```

### 6.2 タブ構成

| タブ | API | フィルター | Assignee列 | Start ボタン | 説明 |
|------|-----|-----------|-----------|-------------|------|
| 全体 (All) | `GET /api/task-list/all` | ユーザーフィルター表示 | 表示 | **非表示** | 全アイテム（全員閲覧可） |
| 自分 (Mine) | `GET /api/task-list/mine` | 非表示 | 非表示 | **表示** | 自分にアサインされたアイテム |

**ユーザーフィルター**（全体タブのみ）:
- 「全員」（デフォルト）→ 全件表示
- 「未割当」→ `?assignee_id=0`
- ユーザー名 → `?assignee_id=N`

ユーザー一覧は `GET /api/users/` で取得し、ドロップダウンに動的追加。

**表示ソート順**: `in_progress` → `open` → `done`（ステータス優先でソート後、サーバー側のデフォルト順を維持）

### 6.3 テーブル列

| 列 | 説明 |
|------|------|
| Status | ステータスバッジ（`open` = グレー、`in_progress` = 青、`done` = 緑） |
| Title | `escapeHtml` でサニタイズ。説明文がある場合は先頭80文字を小文字で表示 |
| Category | タスク分類名バッジ（設定時のみ）。カテゴリは API 取得してクライアントサイドで解決 |
| Assignee | 担当者名（全体タブのみ表示）。`allUsers` マップで解決 |
| Date | 予定日（設定時のみ） |
| Time | 蓄積時間を `Xh Ym` 形式表示（0 秒の場合は非表示） |
| Backlog | `https://ottsystems.backlog.com/view/{ticket}` へのリンクバッジ |
| Actions | 操作ボタン群 |

### 6.4 操作ボタン

| ボタン | 条件 | 説明 |
|--------|------|------|
| Assign | 未割当アイテムのみ | 自分にアサイン |
| Unassign | アサイン済 + `status !== "in_progress"` | アサイン解除（開始済は変更不可） |
| Start | **自分(Mine)タブのみ** + `status !== "done"` | Task にコピーして作業開始 |
| Edit | 常時表示 | 編集モーダルを表示 |
| Done | `status !== "done"` | ステータスを done に更新 |
| Delete | 常時表示 | 確認ダイアログ後に削除 |

- Start ボタンは **自分(Mine)タブでのみ表示**。全体(All)タブでは非表示。Mine タブでは全アイテムが自分にアサイン済のため、担当者チェックは不要。
- **Stop ボタンは TaskList に存在しない**。タイマー停止・タスク完了は Tasks 画面で行う。Tasks で Done すると、TaskListItem のステータスが自動更新される（セクション 3.1 参照）。
- 全操作ボタン（Assign/Unassign/Start 以外）は全認証ユーザーに表示される。

### 6.5 インライン編集

**インライン編集行（作成/編集 共用）**:
- テーブル行がそのまま編集フォームに変わるインライン方式（モーダルなし）
- フィールド: Title（必須）、Description、Scheduled Date、Category（ドロップダウン）、Backlog Ticket
- 新規作成: テーブル先頭に編集行を挿入
- 編集: 既存行を編集行に置換
- Enter キーで保存、Escape キーでキャンセル
- 同時に 1 行のみ編集可能（新規編集開始時に前回の編集をキャンセル）

---

## 7. ビジネスルール

### 7.1 可視性

| アイテム状態 | 閲覧可能なユーザー |
|------------|------------------|
| 未割当（`assignee_id IS NULL`） | 全認証ユーザー |
| 割当済（`assignee_id IS NOT NULL`） | **全認証ユーザー** |

全アイテムが全認証ユーザーに公開される。チーム全体のバックログ可視化のため、可視性制限は設けない。

### 7.2 編集権限

| アイテム状態 | 編集/削除が可能なユーザー |
|------------|------------------------|
| 全アイテム | **全認証ユーザー** |

チーム共有バックログのため、編集・削除に権限制限は設けない。全認証ユーザーが全アイテムを編集・削除可能。

### 7.3 アサイン

| ルール | 説明 |
|--------|------|
| 自己アサインのみ | Assign は自分自身へのアサインのみ可能 |
| 他ユーザーアサイン済の拒否 | 他ユーザーにアサイン済のアイテムへの Assign は `403` |
| 再アサイン | 既に自分にアサイン済の場合は冪等（そのまま返却） |
| 作成時アサイン | `TaskListItemCreate` で `assignee_id` を指定して作成時にアサイン可能 |
| **Unassign 制限** | `status` が `in_progress` のアイテムはアサイン解除不可（`403`） |

### 7.4 Start の重複制限

| ルール | 説明 |
|--------|------|
| 同一アイテムの制限 | 同じ `source_item_id` を持つ Task が既に存在する場合、Start はブロック（`400`） |
| 異なるアイテム | 異なる TaskListItem からの Start は制限なし（複数の Task を同時に持てる） |
| 再 Start 条件 | リンク先 Task が Done / 削除されてなくなれば、同じアイテムから再度 Start 可能 |
| チェック対象 | `db.query(Task).filter(Task.source_item_id == item.id).first()` — DB に存在するもの全て |

### 7.5 時間蓄積

| ルール | 説明 |
|--------|------|
| Done 時の蓄積 | Task の Done（単一/Batch）で `total_seconds` がソース TaskListItem の `total_seconds` に加算される |
| 蓄積条件 | `source_item_id` が設定されており、かつ `total_seconds > 0` の場合のみ |
| 蓄積の累積 | 同一アイテムから Start → Done を繰り返すと、各回の作業時間が累積的に加算される |
| Task 削除後 | Task 削除後も TaskListItem の蓄積時間は保持される |

### 7.6 ステータス同期

| ルール | 説明 |
|--------|------|
| 自動リセット | Task Done 時に、リンクされた全 Task が 0 件になったら `in_progress` → `open` に戻す |
| 部分完了 | 複数 Task がリンクされている場合、1 つ Done しても残りがあれば `in_progress` のまま |
| done は不変 | 手動で `done` に設定されたアイテムは自動リセットの対象外 |
| batch_done 対応 | Batch-Done でも同様に、各 `source_item_id` に対してリンク残数をチェック |

### 7.7 その他

| ルール | 説明 |
|--------|------|
| サーバーソート | `scheduled_date ASC NULLS LAST` → `created_at ASC` |
| クライアントソート | ステータス優先: `in_progress(0)` → `open(1)` → `done(2)` |
| Backlog 連携 | `backlog_ticket_id` でBacklogチケットと紐付け。URL: `https://ottsystems.backlog.com/view/{ticket}` |
| カテゴリ連携 | Start 時に `category_id` が Task にコピーされる |

---

## 8. ファイル構成

### 8.1 新規作成（8 ファイル）

| ファイル | 内容 |
|---------|------|
| `app/models/task_list_item.py` | TaskListItem モデル |
| `app/schemas/task_list_item.py` | リクエスト/レスポンススキーマ |
| `app/crud/task_list_item.py` | CRUD 操作 |
| `app/services/task_list_service.py` | ビジネスロジック（可視性・権限・Start・アサイン） |
| `app/routers/api_task_list.py` | API エンドポイント |
| `templates/task_list.html` | 画面テンプレート |
| `static/js/task_list.js` | フロントエンド JS |
| `tests/test_task_list.py` | テスト（32 件） |

### 8.2 変更（8 ファイル）

| ファイル | 変更内容 |
|---------|---------|
| `app/models/task.py` | `source_item_id` カラム追加 |
| `app/models/__init__.py` | `TaskListItem` import 追加 |
| `app/schemas/task.py` | `source_item_id` フィールド追加 |
| `app/crud/task.py` | `count_by_source_item_id()` 追加（ステータス同期用） |
| `app/services/task_service.py` | done / batch-done に時間蓄積 + ステータス同期ロジック追加 |
| `main.py` | router 登録追加 |
| `app/routers/pages.py` | `/task-list` ページルート追加 |
| `templates/base.html` | Todo 非表示 + Task List ナビ追加 |

---

## 10. マイグレーション

- Revision: `72671cad997f`（`d5e6f7a8b9c0` の次）
- `task_list_items` テーブル作成（全カラム + FK 制約）
- `tasks.source_item_id` カラム追加（FK → `task_list_items.id`, `ON DELETE SET NULL`）
