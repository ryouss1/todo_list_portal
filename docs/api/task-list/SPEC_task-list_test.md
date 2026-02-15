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
親子関係によるサブタスク構造もサポートする。

### 1.3 データフロー

```
TaskListItem (バックログ) → [Start] → Task (タイマー管理) → [Done] → 時間を TaskListItem に蓄積
                                ↑ 何度でもコピー可能
```

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
| parent_id | INTEGER | FK → task_list_items.id (CASCADE), NULL 可 | 親アイテムID |
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
  │                    ├──[Start]──▶ (追加の Task を作成、ステータス変化なし)
  │                    │
  └──[Done(手動)]──────┘──▶ done
```

- **open**: 初期状態。未着手のアイテム
- **in_progress**: Start 操作で Task にコピーされた状態。複数回 Start 可能
- **done**: 手動でステータスを done に変更。完了状態

Start は同一アイテムから複数回実行可能（毎回新しい Task が作成される）。

---

## 4. API エンドポイント

認証: 全エンドポイントで必要（`Depends(get_current_user_id)`）
権限: アクセス制御はセクション 7 の可視性・編集権限ルールに準拠

### 4.1 一覧取得

| メソッド | パス | 説明 | レスポンス |
|---------|------|------|-----------|
| GET | `/api/task-list/unassigned` | 未割当のトップレベルアイテム一覧 | `200` TaskListItemResponse[] |
| GET | `/api/task-list/mine` | 自分に割り当てられたトップレベルアイテム一覧 | `200` TaskListItemResponse[] |

ソート順: `scheduled_date ASC NULLS LAST` → `created_at ASC`

トップレベルのみ取得（`parent_id IS NULL`）。子アイテムは別途取得する。

### 4.2 CRUD

| メソッド | パス | 説明 | レスポンス |
|---------|------|------|-----------|
| POST | `/api/task-list/` | アイテム作成 | `201` TaskListItemResponse |
| GET | `/api/task-list/{id}` | アイテム取得 | `200` TaskListItemResponse / `404` |
| PUT | `/api/task-list/{id}` | アイテム更新 | `200` TaskListItemResponse / `403` / `404` |
| DELETE | `/api/task-list/{id}` | アイテム削除（CASCADE で子アイテムも削除） | `204` / `403` / `404` |

### 4.3 サブタスク

| メソッド | パス | 説明 | レスポンス |
|---------|------|------|-----------|
| GET | `/api/task-list/{id}/children` | 子アイテム一覧 | `200` TaskListItemResponse[] / `404` |

子アイテムの作成は `POST /api/task-list/` で `parent_id` を指定する。

### 4.4 アサイン

| メソッド | パス | 説明 | レスポンス |
|---------|------|------|-----------|
| POST | `/api/task-list/{id}/assign` | 自分にアサイン | `200` TaskListItemResponse / `403` 他ユーザーにアサイン済 / `404` |
| POST | `/api/task-list/{id}/unassign` | アサイン解除 | `200` TaskListItemResponse / `403` / `404` |

### 4.5 Start（タスク変換）

| メソッド | パス | 説明 | レスポンス |
|---------|------|------|-----------|
| POST | `/api/task-list/{id}/start` | アイテムを Task にコピーして開始 | `200` TaskResponse / `404` |

Start 処理の流れ:
1. アイテムの可視性チェック
2. 新しい Task を作成（フィールドをコピー）
   - `title`, `description`, `category_id`, `backlog_ticket_id` → Task にコピー
   - `source_item_id` → アイテムの `id` を設定
   - `user_id` → 現在のユーザー
3. アイテムの `status` を `in_progress` に更新
4. TaskResponse を返却

---

## 5. スキーマ

### TaskListItemCreate
```json
{
  "title": "string (必須)",
  "description": "string (任意)",
  "scheduled_date": "date (任意)",
  "parent_id": "int (任意)",
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
  "parent_id": "int|null",
  "status": "open|in_progress|done",
  "total_seconds": 0,
  "category_id": "int|null",
  "backlog_ticket_id": "string|null",
  "created_at": "datetime",
  "updated_at": "datetime|null",
  "children": "TaskListItemResponse[]|null"
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
├── 担当者なし（Unassigned）── 全員に公開
│   └── カード一覧（Assign / Start / Sub / Edit / Done / Delete）
└── 自分の担当（My Items）
    └── カード一覧（Unassign / Start / Sub / Edit / Done / Delete）
```

### 6.2 2セクション構成

| セクション | アイコン | API | 説明 |
|-----------|---------|-----|------|
| Unassigned | `bi-people` | `GET /api/task-list/unassigned` | 未割当アイテム（全員閲覧可） |
| My Items | `bi-person-check` | `GET /api/task-list/mine` | 自分にアサインされたアイテム |

### 6.3 カード内容

| 要素 | 説明 |
|------|------|
| タイトル | `escapeHtml` でサニタイズ |
| ステータスバッジ | `open` = グレー、`in_progress` = 青、`done` = 緑 |
| カテゴリバッジ | タスク分類名を表示（設定時のみ）。カテゴリは API 取得してクライアントサイドで解決 |
| 説明文 | 任意表示 |
| 予定日 | カレンダーアイコン付きで表示（設定時のみ） |
| 蓄積時間 | 時計アイコン付きで `Xh Ym` 形式表示（0 秒の場合は非表示） |
| Backlog チケットバッジ | `https://ottsystems.backlog.com/view/{ticket}` へのリンクバッジ |

### 6.4 操作ボタン

| ボタン | Unassigned | My Items | 条件 | 説明 |
|--------|-----------|----------|------|------|
| Assign | 表示 | - | - | 自分にアサイン → My Items に移動 |
| Unassign | - | 表示 | - | アサイン解除 → Unassigned に移動 |
| Start | 表示 | 表示 | `status !== "done"` | Task にコピーして作業開始 |
| Sub | 表示 | 表示 | - | サブタスクモーダルを表示 |
| Edit | 表示 | 表示 | - | 編集モーダルを表示 |
| Done | 表示 | 表示 | `status !== "done"` | ステータスを done に更新 |
| Delete | 表示 | 表示 | - | 確認ダイアログ後に削除 |

### 6.5 モーダル

**アイテムモーダル（作成/編集/サブタスク作成 共用）**:
- フィールド: Title（必須）、Description、Scheduled Date、Category（ドロップダウン）、Backlog Ticket
- 新規作成: `parent_id` 空
- サブタスク作成: `parent_id` に親アイテム ID を設定
- 編集: `item-id` に既存アイテム ID を設定

**サブタスクモーダル**:
- 親アイテムの子一覧を表示
- 各子アイテム: タイトル + カテゴリバッジ + ステータスバッジ + 蓄積時間
- 操作ボタン: Start、Done（`status !== "done"` 時）、Delete
- 「Add Sub-task」ボタンでアイテムモーダルを子作成モードで開く

---

## 7. ビジネスルール

### 7.1 可視性

| アイテム状態 | 閲覧可能なユーザー |
|------------|------------------|
| 未割当（`assignee_id IS NULL`） | 全認証ユーザー |
| 割当済（`assignee_id IS NOT NULL`） | 担当者（`assignee_id`）+ 作成者（`created_by`）のみ |

不可視のアイテムにアクセスした場合は `404` を返す（情報漏洩防止）。

### 7.2 編集権限

| アイテム状態 | 編集/削除が可能なユーザー |
|------------|------------------------|
| 未割当 | 作成者のみ |
| 割当済 | 担当者 または 作成者 |

権限がない場合は `403` を返す。

### 7.3 アサイン

| ルール | 説明 |
|--------|------|
| 自己アサインのみ | Assign は自分自身へのアサインのみ可能 |
| 他ユーザーアサイン済の拒否 | 他ユーザーにアサイン済のアイテムへの Assign は `403` |
| 再アサイン | 既に自分にアサイン済の場合は冪等（そのまま返却） |
| 作成時アサイン | `TaskListItemCreate` で `assignee_id` を指定して作成時にアサイン可能 |

### 7.4 時間蓄積

| ルール | 説明 |
|--------|------|
| Done 時の蓄積 | Task の Done（単一/Batch）で `total_seconds` がソース TaskListItem の `total_seconds` に加算される |
| 蓄積条件 | `source_item_id` が設定されており、かつ `total_seconds > 0` の場合のみ |
| 複数回 Start | 同一アイテムから複数回 Start して複数 Task を作成可能。各 Task の時間がそれぞれ蓄積される |
| Task 削除後 | Task 削除後も TaskListItem の蓄積時間は保持される |

### 7.5 サブタスク

| ルール | 説明 |
|--------|------|
| 親子関係 | `parent_id` で 1 階層の親子関係をサポート |
| CASCADE 削除 | 親アイテム削除時に子アイテムも自動削除 |
| トップレベル除外 | 子アイテムは unassigned/mine の一覧には表示されない |
| 親の存在チェック | `parent_id` が指定された場合、親アイテムの存在を検証（`404`） |

### 7.6 その他

| ルール | 説明 |
|--------|------|
| ソートルール | `scheduled_date ASC NULLS LAST` → `created_at ASC` |
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
| `tests/test_task_list.py` | テスト（24 件） |

### 8.2 変更（7 ファイル）

| ファイル | 変更内容 |
|---------|---------|
| `app/models/task.py` | `source_item_id` カラム追加 |
| `app/models/__init__.py` | `TaskListItem` import 追加 |
| `app/schemas/task.py` | `source_item_id` フィールド追加 |
| `app/services/task_service.py` | done / batch-done に時間蓄積ロジック追加 |
| `main.py` | router 登録追加 |
| `app/routers/pages.py` | `/task-list` ページルート追加 |
| `templates/base.html` | Todo 非表示 + Task List ナビ追加 |

---

## 9. テスト

`tests/test_task_list.py` に 32 テストケース。

### セットアップ
- `clean_tasks` (autouse fixture): テスト前に user_id=1 の既存 Task をクリーンアップ（重複制限テストへの干渉防止）
- `test_category` fixture: FK 参照用のテストカテゴリ作成

### CRUD テスト（8 件）
- アイテム作成（基本、全フィールド、title 必須バリデーション）
- アイテム取得
- アイテム更新（タイトル変更、ステータス変更）
- アイテム削除
- 作成時アサイン指定

### アサインテスト（4 件）
- 未割当一覧の確認
- Assign で My Items に移動
- Unassign で未割当プールに復帰
- 他ユーザーアサイン済アイテムへの Assign 拒否（403）

### Start テスト（3 件）
- Start で Task 作成 + フィールドコピー + `source_item_id` 設定確認
- Start でアイテムの status が `in_progress` に変更されることの確認
- 同一アイテムからの 2 回目 Start がブロックされることの確認（400）

### 時間蓄積テスト（2 件）
- Task Done 時に `total_seconds` がソースアイテムに蓄積されることの確認
- Task Done 後もソースアイテムが削除されないことの確認

### ステータス同期テスト（2 件）
- Task Done でリンク元 TaskListItem のステータスが `in_progress` → `open` にリセットされることの確認
- 複数 Task がリンクされている場合、1 つ Done でも残りがあれば `in_progress` のまま維持されることの確認

### 認可テスト（2 件）
- 全アイテムが全ユーザーに可視であることの確認
- 作成者はアサイン済アイテムを閲覧できることの確認

### 全件一覧テスト（3 件）
- `GET /all` が全アイテム（自分/他人/未割当）を返すことの確認
- `GET /all?assignee_id=N` で特定ユーザーフィルターの確認
- `GET /all?assignee_id=0` で未割当フィルターの確認

### 編集・Start・Unassign 権限テスト（4 件）
- 他ユーザーのアイテムを編集・削除できることの確認
- 未アサイン/他ユーザーアサイン済アイテムの Start 拒否（403）
- 自分にアサイン済アイテムの Start 成功
- `in_progress` アイテムの Unassign 拒否（403）

### Start 重複制限テスト（3 件）
- 同一アイテムから Task が既に存在する場合の Start ブロック確認（400）
- 異なるアイテムからの Start は許可されることの確認
- Task Done 後に同一アイテムから再 Start 可能なことの確認

### ページアクセステスト（1 件）
- `/task-list` ルートのアクセス可否確認

