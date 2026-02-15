## 15. Task List API (`/api/task-list`)

### GET /api/task-list/unassigned
担当者なし（未割当）のトップレベルアイテム一覧を取得する。予定日昇順（NULL末尾）、作成日時昇順でソート。

- **レスポンス**: `200 OK` - `TaskListItemResponse[]`

### GET /api/task-list/mine
自分が担当のトップレベルアイテム一覧を取得する。

- **レスポンス**: `200 OK` - `TaskListItemResponse[]`

### POST /api/task-list/
新しいアイテムを作成する。

- **リクエストボディ**: `TaskListItemCreate`

| フィールド | 型 | 必須 | 説明 |
|------------|-----|------|------|
| title | string | Yes | タイトル |
| description | string | No | 説明 |
| scheduled_date | date | No | 予定日 |
| category_id | integer | No | タスク分類ID |
| backlog_ticket_id | string | No | Backlogチケット番号 |
| assignee_id | integer | No | 担当者ID |

- **レスポンス**: `201 Created` - `TaskListItemResponse`

### GET /api/task-list/{id}
アイテムを取得する。未割当アイテムは全ユーザー閲覧可、割当済みアイテムは担当者と作成者のみ閲覧可。

- **レスポンス**: `200 OK` - `TaskListItemResponse`
- **エラー**: `404 Not Found` - アイテム不存在 or アクセス権なし

### PUT /api/task-list/{id}
アイテムを更新する（担当者 or 作成者のみ）。

- **リクエストボディ**: `TaskListItemUpdate`

| フィールド | 型 | 必須 | 説明 |
|------------|-----|------|------|
| title | string | No | タイトル |
| description | string | No | 説明 |
| scheduled_date | date | No | 予定日 |
| category_id | integer | No | タスク分類ID |
| backlog_ticket_id | string | No | Backlogチケット番号 |
| status | string | No | ステータス (open/in_progress/done) |

- **レスポンス**: `200 OK` - `TaskListItemResponse`
- **エラー**: `404 Not Found` / `403 Forbidden`

### DELETE /api/task-list/{id}
アイテムを削除する。担当者 or 作成者のみ。

- **レスポンス**: `204 No Content`
- **エラー**: `404 Not Found` / `403 Forbidden`

### POST /api/task-list/{id}/assign
アイテムを自分に担当割り当てする。未割当のアイテムのみ可能。

- **レスポンス**: `200 OK` - `TaskListItemResponse`
- **エラー**: `404 Not Found` / `403 Forbidden` - 他ユーザーに割当済み

### POST /api/task-list/{id}/unassign
アイテムの担当を解除し、未割当（公開プール）に戻す。担当者 or 作成者のみ。

- **レスポンス**: `200 OK` - `TaskListItemResponse`
- **エラー**: `404 Not Found` / `403 Forbidden`

### POST /api/task-list/{id}/start
アイテムをTasksにコピーして作業を開始する。新しいTaskを作成し、アイテムのステータスを `in_progress` に変更する。何度でも実行可能（同一アイテムから複数Task作成可）。

- **レスポンス**: `200 OK` - `TaskResponse`（作成されたTask）
- **エラー**: `404 Not Found`

### TaskListItemResponse スキーマ

| フィールド | 型 | 説明 |
|------------|-----|------|
| id | integer | アイテムID |
| title | string | タイトル |
| description | string \| null | 説明 |
| scheduled_date | date \| null | 予定日 |
| assignee_id | integer \| null | 担当者ID |
| created_by | integer | 作成者ID |
| status | string | ステータス (open/in_progress/done) |
| total_seconds | integer | 累計作業時間（秒） |
| category_id | integer \| null | タスク分類ID |
| backlog_ticket_id | string \| null | Backlogチケット番号 |
| created_at | datetime | 作成日時 |
| updated_at | datetime \| null | 更新日時 |

---
