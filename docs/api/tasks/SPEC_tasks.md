# Task 機能仕様書

> タスクタイマー機能の完全な仕様。作業時間の計測、日報連携、期限切れ一括完了、TaskList 連携を含む。

---

## 1. 概要

Task 機能はユーザーごとの作業タスクを管理し、タイマーで作業時間を計測する。
タスク完了時に Daily Report を自動作成するオプション（report フラグ）を備え、
前日以前に残ったタスクを一括完了する Batch-Done 機能も提供する。

TaskList から Start 操作で生成されたタスクは `source_item_id` でリンクされ、
Done 時に作業時間の蓄積とステータス同期が行われる。

---

## 2. データモデル

### 2.1 tasks テーブル

| カラム | 型 | 制約 | 説明 |
|--------|------|------|------|
| id | INTEGER | PK, AUTO INCREMENT | タスクID |
| user_id | INTEGER | FK → users.id, NOT NULL | 所有ユーザー |
| title | VARCHAR(500) | NOT NULL | タスクタイトル |
| description | TEXT | NULL 可 | タスクの説明 |
| status | VARCHAR(20) | DEFAULT "pending" | ステータス（`pending` / `in_progress`） |
| total_seconds | INTEGER | DEFAULT 0 | 累計作業時間（秒） |
| report | BOOLEAN | DEFAULT false | 完了時に日報を自動作成するか |
| category_id | INTEGER | FK → task_categories.id, NULL 可 | タスク分類ID |
| backlog_ticket_id | VARCHAR(50) | NULL 可 | Backlogチケット番号（例: WHT-488） |
| source_item_id | INTEGER | FK → task_list_items.id (SET NULL), NULL 可 | コピー元の TaskListItem ID |
| created_at | DATETIME(TZ) | server_default=now() | 作成日時 |
| updated_at | DATETIME(TZ) | server_default=now(), onupdate=now() | 更新日時 |

`source_item_id` は TaskList の Start 操作で自動設定される。TaskListItem が削除されても Task 側は `SET NULL` で残存する。

### 2.2 task_time_entries テーブル

| カラム | 型 | 制約 | 説明 |
|--------|------|------|------|
| id | INTEGER | PK, AUTO INCREMENT | エントリID |
| task_id | INTEGER | FK → tasks.id (CASCADE), NOT NULL | タスクID |
| started_at | DATETIME(TZ) | NOT NULL | 開始日時（UTC） |
| stopped_at | DATETIME(TZ) | NULL 可 | 停止日時（NULL = 稼働中） |
| elapsed_seconds | INTEGER | DEFAULT 0 | 経過秒数 |
| created_at | DATETIME(TZ) | server_default=now() | 作成日時 |

---

## 3. ステータス遷移

```
pending ──[Start]──▶ in_progress ──[Stop]──▶ pending
   │                      │
   └──────[Done]──────────┘──▶ (削除)
                                  ↓
                          TaskListItem に時間蓄積 + ステータス同期
```

- **pending**: 初期状態、またはタイマー停止後の状態
- **in_progress**: タイマー稼働中
- Done 操作でタスクは削除される（completed ステータスは存在しない）

---

## 4. API エンドポイント

認証: 全エンドポイントで必要（`Depends(get_current_user_id)`）
権限: 自分のタスクのみ操作可能（他ユーザーのタスクは 404）

### 4.1 CRUD

| メソッド | パス | 説明 | レスポンス |
|---------|------|------|-----------|
| GET | `/api/tasks/` | タスク一覧（created_at 降順） | `200` TaskResponse[] |
| POST | `/api/tasks/` | タスク作成 | `201` TaskResponse |
| GET | `/api/tasks/{id}` | タスク取得 | `200` TaskResponse / `404` |
| PUT | `/api/tasks/{id}` | タスク更新 | `200` TaskResponse / `404` |
| DELETE | `/api/tasks/{id}` | タスク削除（CASCADE で time_entries も削除） | `204` / `404` |

### 4.2 タイマー

| メソッド | パス | 説明 | レスポンス |
|---------|------|------|-----------|
| POST | `/api/tasks/{id}/start` | タイマー開始 | `200` TimeEntryResponse / `400` 稼働中 / `404` |
| POST | `/api/tasks/{id}/stop` | タイマー停止 | `200` TimeEntryResponse / `400` 非稼働 / `404` |
| GET | `/api/tasks/{id}/time-entries` | タイムエントリ一覧（started_at 降順） | `200` TimeEntryResponse[] / `404` |

### 4.3 Done（単一タスク完了）

| メソッド | パス | 説明 | レスポンス |
|---------|------|------|-----------|
| POST | `/api/tasks/{id}/done` | タスク完了 | `200` DailyReportResponse（report=true 時）/ `204`（report=false 時）/ `404` |

Done 処理の流れ:
1. タイマー稼働中なら現在時刻で停止
2. `report=true` の場合 → `DailyReport` を作成（`report_date = today`）
   - `category_id`: タスクの `category_id`（未設定時は `DEFAULT_CATEGORY_ID=7`）
   - `work_content`: `"{title} ({Xh Ym})\n{description}"`
3. `source_item_id` と `total_seconds` を退避
4. タスクを削除（CASCADE で time_entries も削除）
5. **TaskListItem 連携**（`source_item_id` が非 NULL の場合）:
   - `total_seconds > 0` なら作業時間をソース TaskListItem に蓄積
   - リンクされた他の Task が残っていなければ、TaskListItem の status を `in_progress` → `open` に自動リセット

### 4.4 Batch-Done（一括完了）

| メソッド | パス | 説明 | レスポンス |
|---------|------|------|-----------|
| POST | `/api/tasks/batch-done` | 期限切れタスク一括完了 | `200` BatchDoneResponse / `404` |

**リクエスト**:
```json
{
  "tasks": [
    { "task_id": 1, "end_time": "18:00" },
    { "task_id": 2, "end_time": "17:30" }
  ]
}
```

**レスポンス**:
```json
{
  "results": [
    { "task_id": 1, "report_id": null },
    { "task_id": 2, "report_id": 5 }
  ]
}
```

Batch-Done 処理の流れ（各タスクに対して）:
1. 所有権チェック（他ユーザーのタスクは `404`）
2. `updated_at` のローカル日付を取得 → `task_date`
3. `end_time`（HH:MM）+ `task_date` → UTC datetime に変換（ローカル TZ として解釈）
4. タイマー稼働中なら `end_time` の時刻で停止（`stop_timer_at`、flush のみ）
5. `report=true` の場合 → `DailyReport` を作成（`report_date = task_date`、flush のみ）
6. `source_item_id` と `total_seconds` を退避
7. タスクを削除（flush のみ）
8. **TaskListItem 連携**: `total_seconds > 0` なら作業時間をソース TaskListItem に蓄積（flush のみ）

ループ終了後:
9. **ステータス同期**: 各 `source_item_id` に対してリンクされた Task の残数をチェック。0 件なら `in_progress` → `open` に自動リセット（flush のみ）
10. 最後に一括 commit。1 タスクでもエラーなら全体ロールバック。

---

## 5. スキーマ

### TaskCreate
```json
{
  "title": "string (必須)",
  "description": "string (任意)",
  "report": false,
  "category_id": "int (任意)",
  "backlog_ticket_id": "string (任意)"
}
```

### TaskUpdate
```json
{
  "title": "string (任意)",
  "description": "string (任意)",
  "report": "bool (任意)",
  "category_id": "int (任意)",
  "backlog_ticket_id": "string (任意)"
}
```

### TaskResponse
```json
{
  "id": 1,
  "user_id": 1,
  "title": "string",
  "description": "string|null",
  "status": "pending|in_progress",
  "total_seconds": 0,
  "report": false,
  "category_id": "int|null",
  "backlog_ticket_id": "string|null",
  "source_item_id": "int|null",
  "created_at": "datetime",
  "updated_at": "datetime|null"
}
```

### TimeEntryResponse
```json
{
  "id": 1,
  "task_id": 1,
  "started_at": "datetime",
  "stopped_at": "datetime|null",
  "elapsed_seconds": 0,
  "created_at": "datetime"
}
```

### BatchDoneRequest / BatchDoneResponse
```json
// Request
{ "tasks": [{ "task_id": 1, "end_time": "HH:MM" }] }
// Response
{ "results": [{ "task_id": 1, "report_id": null }] }
```

---

## 6. フロントエンド

### 6.1 画面構成（`/tasks`）

- テンプレート: `templates/tasks.html`
- JavaScript: `static/js/tasks.js?v=8`
- カード形式のグリッド表示（MD: 2列、LG: 3列）

### 6.2 カード内容

| 要素 | 説明 |
|------|------|
| タイトル | `escapeHtml` でサニタイズ |
| ステータスバッジ | `pending` = グレー、`in_progress` = 青 |
| カテゴリバッジ | タスク分類名を表示（設定時のみ） |
| 説明文 | 任意表示 |
| Backlog チケットバッジ | チケット番号が設定されている場合、クリッカブルなリンクバッジを表示（`https://{BACKLOG_SPACE}.backlog.com/view/{ticket}`） |
| Report チェックボックス | `toggleReport()` で即時 API 更新 |
| タイマー表示 | HH:MM:SS 形式、稼働中は 1 秒ごとにリアルタイム更新 |
| Start / Stop ボタン | Start → `loadTasks()` で全体再描画、Stop → `loadTasks()` で全体再描画 |
| Done ボタン | 確認ダイアログ後にタスク完了 |
| Edit / Delete ボタン | カードフッターに配置 |

### 6.3 Overdue モーダル

ページ読み込み時に `updated_at` の日付 < 今日のタスクを検出し、該当がある場合に強制表示。

- `data-bs-backdrop="static"` + `data-bs-keyboard="false"` で閉じるボタンなし（強制入力）
- 各タスク: タイトル + 日付 + time input（デフォルト 18:00）
- "Complete All" ボタンで `POST /api/tasks/batch-done` → ページ再読み込み

### 6.4 アクティブタイマーの自動検出

ページ読み込み時に全タスクの `time-entries` を取得し、
`stopped_at === null` のエントリがあればタイマーのカウントアップを再開する。

---

## 7. ビジネスルール

### 7.1 基本ルール

| ルール | 説明 |
|--------|------|
| 所有権 | 自分のタスクのみ操作可能。他ユーザーのタスクは 404 |
| タイマー排他 | 同一タスクで同時に複数のタイマーは稼働不可（400） |
| タイマー開始 | `TaskTimeEntry` 作成 + `status = in_progress` |
| タイマー停止 | `elapsed_seconds` 計算 + `total_seconds` に加算 + `status = pending` |
| Done | タイマー停止 → レポート作成（任意）→ TaskListItem 連携 → タスク削除 |
| Batch-Done | 指定時刻でタイマー停止 → レポート作成（任意）→ TaskListItem 連携 → タスク削除 |
| CASCADE 削除 | タスク削除時に関連する `task_time_entries` も自動削除 |

### 7.2 日報連携

| ルール | 説明 |
|--------|------|
| report フラグ | true の場合、Done/Batch-Done 時に `DailyReport` を自動作成 |
| カテゴリ連携 | タスクの `category_id` を使用（未設定時は `DEFAULT_CATEGORY_ID=7` "その他"） |
| レポート内容 | `"{title} ({Xh Ym})"` + 改行 + `"{description}"` |
| report_date | Done → `today`、Batch-Done → タスクの `task_date`（`updated_at` のローカル日付） |

### 7.3 Backlog 連携

| ルール | 説明 |
|--------|------|
| チケット番号 | 任意で `backlog_ticket_id` を登録可能 |
| URL 生成 | `https://{BACKLOG_SPACE}.backlog.com/view/{ticket}` |
| Presence 連携 | Presence 画面で `in_progress` タスクのチケットを URL リンクとして表示 |

### 7.4 TaskListItem 連携

| ルール | 説明 |
|--------|------|
| 時間蓄積 | Done/Batch-Done 時に `total_seconds` をソース TaskListItem の `total_seconds` に加算 |
| 蓄積条件 | `source_item_id` が設定されており、かつ `total_seconds > 0` の場合のみ |
| ステータス同期 | Done 後、リンクされた他の Task が 0 件なら TaskListItem を `in_progress` → `open` に自動リセット |
| done は不変 | TaskListItem が手動で `done` に設定されている場合は自動リセットしない |
| Batch-Done 対応 | 全タスク処理後に各 `source_item_id` のリンク残数をまとめてチェック |

---

## 8. ファイル構成

| ファイル | 役割 |
|---------|------|
| `app/models/task.py` | Task モデル（`source_item_id` FK 含む） |
| `app/models/task_time_entry.py` | TaskTimeEntry モデル |
| `app/schemas/task.py` | リクエスト/レスポンススキーマ |
| `app/crud/task.py` | CRUD + タイマー操作 + `count_by_source_item_id` |
| `app/services/task_service.py` | ビジネスロジック（Done/Batch-Done の TaskListItem 連携含む） |
| `app/routers/api_tasks.py` | API エンドポイント |
| `templates/tasks.html` | 画面テンプレート |
| `static/js/tasks.js` | フロントエンド JS（v=8） |
| `tests/test_tasks.py` | テスト（33 件） |

---

## 9. テスト

`tests/test_tasks.py` に 33 テストケース。

### TestTaskAPI（27 件）
- CRUD 基本操作（一覧、作成、取得、更新、削除）
- タイマー（開始、停止、重複開始拒否、非稼働停止拒否）
- タイムエントリ取得
- Done（基本、report 付き、report 内容確認、稼働中タイマー、他ユーザー拒否）
- report フラグ切り替え
- Backlog チケット番号（作成、作成時 null、更新・クリア）
- カテゴリ（作成、作成時 null、更新）
- Done 時のカテゴリ使用（タスク指定カテゴリ、デフォルトカテゴリ）
- バリデーション（title 未指定 → 422）

### TestBatchDone（6 件）
- 単一タスク完了 + 削除確認
- 複数タスク一括完了
- report=true → DailyReport 作成確認
- タイマー稼働中 → 指定時刻停止
- 他ユーザーのタスク拒否（404）
- 空リスト → 正常応答
