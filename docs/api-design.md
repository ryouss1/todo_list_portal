# API仕様

> 本ドキュメントは [spec.md](./spec.md) の補足資料です。

すべてのAPIのベースURL: `/api`

### 認証

- `/api/auth/*` と `POST /api/logs/` を除く全APIエンドポイントは認証が必要。
- 未認証の場合 `401 Unauthorized`（`{"detail": "Not authenticated"}`）を返却する。
- 認証はセッションCookieで管理される（`SessionMiddleware`）。

### 認可

- ログインユーザーは**自分のデータのみ**操作可能。
- 他ユーザーのリソースへのアクセスは `404 Not Found` を返却する（IDの存在を漏洩しない）。
- admin/user ロールによるRBAC制御（`require_admin` 依存性注入）。

| リソース | 一覧取得 | 個別操作 (GET/PUT/DELETE) |
|---------|---------|------------------------|
| Todo | 自分のTodoのみ（公開一覧は全員分） | 自分のTodoのみ |
| Task | 自分のTaskのみ | 自分のTaskのみ |
| Attendance | 自分の記録のみ | 自分の記録のみ |
| Presence | アクティブユーザーの在籍状態閲覧可（is_active=false を除外） | 自分のステータスのみ更新可 |
| Report | 自分の日報 / 全ユーザーの日報 | 閲覧:全員、編集/削除:所有者のみ |
| Summary | 全ユーザーの集約データ（閲覧のみ） | N/A |
| User | 全ユーザー閲覧可（認証必須） | admin:全編集、user:自分のdisplay_nameのみ |
| Log | POST:認証不要、GET:認証必須 | N/A |
| LogSource | 全件閲覧可（認証必須） | CUD:admin のみ |
| Alert | 全件（認証必須） | 確認は認証ユーザーで記録、削除はadminのみ |
| AlertRule | 全件閲覧可（認証必須） | CUD:admin のみ |
| TaskList | 未割当:全ユーザー / 割当済:全ユーザー閲覧可 | 編集/削除:全認証ユーザー |
| TaskCategory | 全件閲覧可（認証必須） | CUD:admin のみ |
| OAuthProvider | 有効プロバイダ一覧は認証不要、管理はadminのみ | admin:全操作 |
| SiteLink | 全件閲覧可（認証必須） | 編集/削除:作成者のみ |
| SiteGroup | 全件閲覧可（認証必須） | CUD:admin のみ |
| WikiPage | 全件閲覧可（認証必須） | 編集/削除:作成者のみ |
| WikiCategory | 全件閲覧可（認証必須） | CUD:admin のみ |
| WikiTag | 全件閲覧可（認証必須） | 作成:全認証ユーザー、削除:admin のみ |

---

## 1. Auth API (`/api/auth`)

### POST /api/auth/login
ログインする。成功時にセッションCookieが設定される。

- **リクエストボディ**: `LoginRequest`

| フィールド | 型 | 必須 | 説明 |
|------------|-----|------|------|
| email | string (EmailStr) | Yes | メールアドレス |
| password | string | Yes | パスワード |

- **レスポンス**: `200 OK` - `LoginResponse`
- **エラー**: `401 Unauthorized` - 認証失敗

### POST /api/auth/logout
ログアウトする。セッションを破棄する。

- **レスポンス**: `204 No Content`

### GET /api/auth/me
ログインユーザーの情報を取得する。

- **レスポンス**: `200 OK` - `LoginResponse`
- **エラー**: `401 Unauthorized` - 未ログイン

### LoginResponse スキーマ

| フィールド | 型 | 説明 |
|------------|-----|------|
| user_id | integer | ユーザーID |
| email | string | メールアドレス |
| display_name | string | 表示名 |
| role | string | ロール (admin/user) |

### GET /api/auth/audit-logs
認証監査ログ一覧を取得する。

- **権限**: admin のみ
- **クエリパラメータ**:

| パラメータ | 型 | デフォルト | 説明 |
|------------|-----|-----------|------|
| limit | integer | 100 | 取得件数上限 |
| user_id | integer | null | ユーザーIDフィルタ |
| event_type | string | null | イベント種別フィルタ |

- **レスポンス**: `200 OK` - `AuditLogResponse[]`

### AuditLogResponse スキーマ

| フィールド | 型 | 説明 |
|------------|-----|------|
| id | integer | ログID |
| user_id | integer \| null | ユーザーID |
| event_type | string | イベント種別 |
| email | string \| null | メールアドレス |
| ip_address | string \| null | IPアドレス |
| user_agent | string \| null | ユーザーエージェント |
| details | object \| null | 追加情報 |
| created_at | datetime | 日時 |

### POST /api/auth/forgot-password
パスワードリセットメールを送信する。ユーザー列挙防止のため、メールの存在有無に関わらず常に200を返却する。

- **権限**: 認証不要
- **リクエストボディ**: `ForgotPasswordRequest`

| フィールド | 型 | 必須 | 説明 |
|------------|-----|------|------|
| email | string (EmailStr) | Yes | メールアドレス |

- **レスポンス**: `200 OK` - `{"detail": "..."}`
- **レート制限**: 15分間に最大3回まで（超過時も200を返却）

### POST /api/auth/validate-reset-token
パスワードリセットトークンの有効性を検証する。

- **権限**: 認証不要
- **リクエストボディ**: `ValidateTokenRequest`

| フィールド | 型 | 必須 | 説明 |
|------------|-----|------|------|
| token | string | Yes | リセットトークン |

- **レスポンス**: `200 OK` - `{"valid": true/false}`

### POST /api/auth/reset-password
パスワードをリセットする。成功時にセッション・全トークンが無効化され、アカウントがアンロックされる。

- **権限**: 認証不要
- **リクエストボディ**: `ResetPasswordRequest`

| フィールド | 型 | 必須 | 説明 |
|------------|-----|------|------|
| token | string | Yes | リセットトークン |
| new_password | string | Yes | 新しいパスワード |

- **レスポンス**: `200 OK` - `{"detail": "..."}`
- **エラー**: `400 Bad Request` - パスワードポリシー違反、`404 Not Found` - トークン不正/期限切れ

---

## 2. OAuth API (`/api/auth/oauth`)

### GET /api/auth/oauth/providers
有効なOAuthプロバイダ一覧を取得する（ログインページ用）。

- **権限**: 認証不要
- **レスポンス**: `200 OK` - `OAuthProviderPublic[]`

### GET /api/auth/oauth/{provider}/authorize
OAuth認証フローを開始する。プロバイダの認証画面にリダイレクトする。

- **権限**: 認証不要
- **レスポンス**: `302 Found` - プロバイダの認証URLにリダイレクト

### GET /api/auth/oauth/{provider}/callback
OAuthコールバックを処理する。認証コードをトークンに交換し、ユーザーを特定してセッションを作成する。

- **権限**: 認証不要
- **クエリパラメータ**: `code` (string, 必須), `state` (string, 必須)
- **レスポンス**: `302 Found` - `/` にリダイレクト（成功時）
- **エラー**: `400 Bad Request` - 無効なstate / ユーザー不明

### POST /api/auth/oauth/{provider}/link
OAuthアカウントを現在のユーザーにリンクする。OAuth認証フローで取得したcodeとstateを使用する。

- **権限**: 認証必要
- **クエリパラメータ**: `code` (string, 必須), `state` (string, 必須)
- **レスポンス**: `200 OK` - `{"detail": "Linked {provider} account"}`
- **エラー**: `400 Bad Request` - 無効なstate / リンク失敗

### DELETE /api/auth/oauth/{provider}/unlink
OAuthアカウントのリンクを解除する。最後の認証手段の場合は拒否される。

- **権限**: 認証必要
- **レスポンス**: `200 OK` - `{"detail": "Unlinked {provider} account"}`
- **エラー**: `400 Bad Request` - 最後の認証手段 / `404 Not Found` - リンクなし

### GET /api/auth/oauth/my-links
自分のOAuthアカウントリンク一覧を取得する。

- **権限**: 認証必要
- **レスポンス**: `200 OK` - `OAuthLinkResponse[]`

### OAuthProviderPublic スキーマ

| フィールド | 型 | 説明 |
|------------|-----|------|
| name | string | プロバイダ名 |
| display_name | string | 表示名 |

### OAuthLinkResponse スキーマ

| フィールド | 型 | 説明 |
|------------|-----|------|
| id | integer | リンクID |
| provider_name | string | プロバイダ名 |
| provider_display_name | string | プロバイダ表示名 |
| provider_email | string \| null | プロバイダ側メール |
| created_at | datetime | リンク日時 |

---

## 3. OAuthプロバイダ管理 API (`/api/admin/oauth-providers`)

### GET /api/admin/oauth-providers/
OAuthプロバイダ一覧を取得する。

- **権限**: admin のみ
- **レスポンス**: `200 OK` - `OAuthProviderResponse[]`

### POST /api/admin/oauth-providers/
OAuthプロバイダを作成する。

- **権限**: admin のみ
- **リクエストボディ**: `OAuthProviderCreate`

| フィールド | 型 | 必須 | 説明 |
|------------|-----|------|------|
| name | string | Yes | プロバイダ名 |
| display_name | string | Yes | 表示名 |
| client_id | string | Yes | OAuth Client ID |
| client_secret | string | Yes | OAuth Client Secret |
| authorize_url | string | Yes | 認証エンドポイント |
| token_url | string | Yes | トークンエンドポイント |
| userinfo_url | string | Yes | ユーザー情報エンドポイント |
| scopes | string | Yes | スコープ（スペース区切り） |

- **レスポンス**: `201 Created` - `OAuthProviderResponse`

### PUT /api/admin/oauth-providers/{id}
OAuthプロバイダを更新する。

- **権限**: admin のみ
- **リクエストボディ**: `OAuthProviderUpdate`（全フィールド任意）
- **レスポンス**: `200 OK` - `OAuthProviderResponse`
- **エラー**: `404 Not Found`

### DELETE /api/admin/oauth-providers/{id}
OAuthプロバイダを削除する。

- **権限**: admin のみ
- **レスポンス**: `204 No Content`
- **エラー**: `404 Not Found`

### OAuthProviderResponse スキーマ

| フィールド | 型 | 説明 |
|------------|-----|------|
| id | integer | プロバイダID |
| name | string | プロバイダ名 |
| display_name | string | 表示名 |
| client_id | string | Client ID |
| authorize_url | string | 認証URL |
| token_url | string | トークンURL |
| userinfo_url | string | ユーザー情報URL |
| scopes | string | スコープ |
| is_enabled | boolean | 有効フラグ |
| created_at | datetime | 作成日時 |
| updated_at | datetime | 更新日時 |

---

## 4. Todo API (`/api/todos`)

### GET /api/todos/
自分のTodo一覧を取得する。

- **レスポンス**: `200 OK` - `TodoResponse[]`

### POST /api/todos/
新しいTodoを作成する。

- **リクエストボディ**: `TodoCreate`

| フィールド | 型 | 必須 | デフォルト | 説明 |
|------------|-----|------|-----------|------|
| title | string | Yes | - | タイトル |
| description | string | No | null | 説明 |
| priority | integer | No | 0 | 優先度 (0=Normal, 1=High, 2=Urgent) |
| due_date | date | No | null | 期日 |
| visibility | string | No | "private" | 公開範囲 (private/public) |

- **レスポンス**: `201 Created` - `TodoResponse`

### GET /api/todos/public
公開Todo一覧を取得する（全ユーザー分）。

- **レスポンス**: `200 OK` - `TodoResponse[]`

### GET /api/todos/{id}
指定IDのTodoを取得する。

- **レスポンス**: `200 OK` - `TodoResponse`
- **エラー**: `404 Not Found`

### PUT /api/todos/{id}
Todoを更新する。

- **リクエストボディ**: `TodoUpdate`（全フィールド任意）
- **レスポンス**: `200 OK` - `TodoResponse`
- **エラー**: `404 Not Found`

### DELETE /api/todos/{id}
Todoを削除する。

- **レスポンス**: `204 No Content`
- **エラー**: `404 Not Found`

### PATCH /api/todos/{id}/toggle
Todoの完了状態をトグルする。

- **レスポンス**: `200 OK` - `TodoResponse`
- **エラー**: `404 Not Found`

### TodoResponse スキーマ

| フィールド | 型 | 説明 |
|------------|-----|------|
| id | integer | Todo ID |
| user_id | integer | ユーザーID |
| title | string | タイトル |
| description | string \| null | 説明 |
| is_completed | boolean | 完了フラグ |
| priority | integer | 優先度 |
| due_date | date \| null | 期日 |
| visibility | string | 公開範囲 |
| created_at | datetime | 作成日時 |
| updated_at | datetime \| null | 更新日時 |

---

## 5. Attendance API (`/api/attendances`)

### POST /api/attendances/clock-in
出勤を記録する。既に出勤中の場合や同日退勤後はエラー。

- **リクエストボディ**: `ClockInRequest`

| フィールド | 型 | 必須 | 説明 |
|------------|-----|------|------|
| note | string | No | メモ |

- **レスポンス**: `201 Created` - `AttendanceResponse`
- **エラー**: `400 Bad Request` - 二重出勤 / 同日再出勤

### POST /api/attendances/clock-out
退勤を記録する。

- **リクエストボディ**: `ClockOutRequest`

| フィールド | 型 | 必須 | 説明 |
|------------|-----|------|------|
| note | string | No | メモ |

- **レスポンス**: `200 OK` - `AttendanceResponse`
- **エラー**: `400 Bad Request` - 未出勤

### GET /api/attendances/status
現在の出勤状態を取得する。

- **レスポンス**: `200 OK` - `AttendanceStatus`

### GET /api/attendances/my-preset
デフォルト出勤プリセットIDを取得する。

- **レスポンス**: `200 OK` - `UserPresetResponse`

### PUT /api/attendances/my-preset
デフォルト出勤プリセットIDを設定する。

- **レスポンス**: `200 OK` - `UserPresetResponse`
- **エラー**: `404 Not Found` - 存在しないプリセット

### POST /api/attendances/default-set
プリセットから当日の勤怠を一括設定する。既存レコードがあれば上書き。

- **レスポンス**: `200 OK` - `AttendanceResponse`
- **エラー**: `400 Bad Request` / `403 Forbidden` - admin記録のロック

### GET /api/attendances/export
月別勤怠データをExcelファイルでエクスポートする。

- **クエリパラメータ**: `year` (integer, 必須), `month` (integer, 必須)
- **レスポンス**: `200 OK` - Excel ファイル (application/vnd.openxmlformats-officedocument.spreadsheetml.sheet)

### GET /api/attendances/
出勤履歴一覧を取得する。

- **クエリパラメータ**: `year` (integer, 任意), `month` (integer, 任意)
- **レスポンス**: `200 OK` - `AttendanceResponse[]`

### POST /api/attendances/
勤怠記録を手動作成する。

- **リクエストボディ**: `AttendanceCreate`
- **レスポンス**: `201 Created` - `AttendanceResponse`
- **エラー**: `400 Bad Request` - 同日重複

### GET /api/attendances/{id}
出勤記録を取得する。

- **レスポンス**: `200 OK` - `AttendanceResponse`
- **エラー**: `404 Not Found`

### PUT /api/attendances/{id}
出勤記録を更新する。

- **リクエストボディ**: `AttendanceUpdate`
- **レスポンス**: `200 OK` - `AttendanceResponse`
- **エラー**: `403 Forbidden` - admin記録のロック / `404 Not Found`

### DELETE /api/attendances/{id}
出勤記録を削除する。

- **レスポンス**: `204 No Content`
- **エラー**: `403 Forbidden` - admin記録のロック / `404 Not Found`

### POST /api/attendances/{id}/break-start
休憩を開始する（最大3回まで）。

- **レスポンス**: `200 OK` - `AttendanceResponse`
- **エラー**: `400 Bad Request` / `403 Forbidden` / `404 Not Found`

### POST /api/attendances/{id}/break-end
休憩を終了する。

- **レスポンス**: `200 OK` - `AttendanceResponse`
- **エラー**: `400 Bad Request` / `404 Not Found`

### AttendanceResponse スキーマ

| フィールド | 型 | 説明 |
|------------|-----|------|
| id | integer | 出勤記録ID |
| user_id | integer | ユーザーID |
| date | date | 出勤日 |
| clock_in | datetime | 出勤日時 |
| clock_out | datetime \| null | 退勤日時 |
| input_type | string | 入力種別 (web/ic_card/admin) |
| note | string \| null | メモ |
| breaks | array | 休憩一覧 |
| created_at | datetime | 作成日時 |
| updated_at | datetime \| null | 更新日時 |

---

## 6. Task API (`/api/tasks`)

### GET /api/tasks/
タスク一覧を作成日時降順で取得する。

- **レスポンス**: `200 OK` - `TaskResponse[]`

### POST /api/tasks/
新しいタスクを作成する。

- **リクエストボディ**: `TaskCreate`

| フィールド | 型 | 必須 | 説明 |
|------------|-----|------|------|
| title | string | Yes | タイトル |
| description | string | No | 説明 |
| category_id | integer | No | タスク分類ID（task_categories.id） |
| backlog_ticket_id | string | No | Backlogチケット番号（例: WHT-488） |

- **レスポンス**: `201 Created` - `TaskResponse`

### POST /api/tasks/batch-done
複数タスクを一括完了する。report=trueのタスクは日報を自動作成。

- **リクエストボディ**: `BatchDoneRequest`
- **レスポンス**: `200 OK` - `BatchDoneResponse`

### GET /api/tasks/{task_id}
指定IDのタスクを取得する。

- **レスポンス**: `200 OK` - `TaskResponse`
- **エラー**: `404 Not Found`

### PUT /api/tasks/{task_id}
指定IDのタスクを更新する。

- **リクエストボディ**: `TaskUpdate`

| フィールド | 型 | 必須 | 説明 |
|------------|-----|------|------|
| title | string | No | タイトル |
| description | string | No | 説明 |
| status | string | No | ステータス (pending/in_progress) |
| category_id | integer | No | タスク分類ID |
| backlog_ticket_id | string | No | Backlogチケット番号 |
| report | boolean | No | Done時日報自動作成フラグ |

- **レスポンス**: `200 OK` - `TaskResponse`
- **エラー**: `404 Not Found`

### DELETE /api/tasks/{task_id}
指定IDのタスクを削除する（関連するtime_entriesもCASCADE削除される）。

- **レスポンス**: `204 No Content`
- **エラー**: `404 Not Found`

### POST /api/tasks/{task_id}/done
タスクを完了する。タスクは物理削除される。report=trueの場合は日報を自動作成して返却する。

- **レスポンス**: `204 No Content`（report=false時）/ `200 OK` - `DailyReportResponse`（report=true時）
- **エラー**: `404 Not Found`

### POST /api/tasks/{task_id}/start
タスクのタイマーを開始する。ステータスは自動的に `in_progress` に変更される。

- **レスポンス**: `200 OK` - `TimeEntryResponse`
- **エラー**:
  - `404 Not Found` - タスク不存在時
  - `400 Bad Request` - `"Timer already running"` タイマー稼働中の場合

### POST /api/tasks/{task_id}/stop
タスクのタイマーを停止する。経過秒数を計算し、タスクの`total_seconds`に加算する。

- **レスポンス**: `200 OK` - `TimeEntryResponse`
- **エラー**:
  - `404 Not Found` - タスク不存在時
  - `400 Bad Request` - `"No active timer"` 稼働中タイマーなしの場合

### GET /api/tasks/{task_id}/time-entries
タスクの時間エントリ一覧を開始日時降順で取得する。

- **レスポンス**: `200 OK` - `TimeEntryResponse[]`
- **エラー**: `404 Not Found`

### TaskResponse スキーマ

| フィールド | 型 | 説明 |
|------------|-----|------|
| id | integer | タスクID |
| user_id | integer | ユーザーID |
| title | string | タイトル |
| description | string \| null | 説明 |
| status | string | ステータス |
| total_seconds | integer | 累計作業時間（秒） |
| report | boolean | Done時日報自動作成フラグ |
| category_id | integer \| null | タスク分類ID |
| backlog_ticket_id | string \| null | Backlogチケット番号 |
| source_item_id | integer \| null | タスクリストアイテムID |
| created_at | datetime | 作成日時 |
| updated_at | datetime \| null | 更新日時 |

### TimeEntryResponse スキーマ

| フィールド | 型 | 説明 |
|------------|-----|------|
| id | integer | エントリID |
| task_id | integer | タスクID |
| started_at | datetime | 開始日時 |
| stopped_at | datetime \| null | 停止日時 |
| elapsed_seconds | integer | 経過秒数 |
| created_at | datetime | 作成日時 |

---

## 7. Task List API (`/api/task-list`)

### GET /api/task-list/unassigned
担当者なし（未割当）のアイテム一覧を取得する。

- **レスポンス**: `200 OK` - `TaskListItemResponse[]`

### GET /api/task-list/mine
自分が担当のアイテム一覧を取得する。

- **クエリパラメータ**:

| パラメータ | 型 | デフォルト | 説明 |
|------------|-----|-----------|------|
| status | List[string] | null | ステータスフィルタ（複数指定可。例: `?status=open&status=in_progress`） |

- **レスポンス**: `200 OK` - `TaskListItemResponse[]`

### GET /api/task-list/all
全アイテム一覧を取得する（担当者/ステータス/キーワードフィルタ対応）。

- **クエリパラメータ**:

| パラメータ | 型 | デフォルト | 説明 |
|------------|-----|-----------|------|
| assignee_id | integer | null | 担当者IDフィルタ（0=未割当） |
| status | List[string] | null | ステータスフィルタ（複数指定可。例: `?status=open&status=in_progress`） |
| q | string | null | タイトル部分一致フィルタ（大文字小文字を区別しない ILIKE 検索） |

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
アイテムを取得する。

- **レスポンス**: `200 OK` - `TaskListItemResponse`
- **エラー**: `404 Not Found`

### PUT /api/task-list/{id}
アイテムを更新する。

- **リクエストボディ**: `TaskListItemUpdate`（全フィールド任意、status含む）
- **レスポンス**: `200 OK` - `TaskListItemResponse`
- **エラー**: `403 Forbidden` / `404 Not Found`

### DELETE /api/task-list/{id}
アイテムを削除する。

- **レスポンス**: `204 No Content`
- **エラー**: `403 Forbidden` / `404 Not Found`

### POST /api/task-list/{id}/assign
アイテムを自分に担当割り当てする。

- **レスポンス**: `200 OK` - `TaskListItemResponse`
- **エラー**: `403 Forbidden` - 他ユーザーに割当済み / `404 Not Found`

### POST /api/task-list/{id}/unassign
アイテムの担当を解除する。

- **レスポンス**: `200 OK` - `TaskListItemResponse`
- **エラー**: `403 Forbidden` / `404 Not Found`

### POST /api/task-list/{id}/start
アイテムをTasksにコピーして作業を開始する。アイテムのステータスを `in_progress` に変更。

- **レスポンス**: `200 OK` - `TaskResponse`（作成されたTask）
- **エラー**: `403 Forbidden` / `404 Not Found`

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

## 8. Task Category API (`/api/task-categories`)

### GET /api/task-categories/
タスク分類一覧を取得する。

- **権限**: 認証済みユーザー
- **レスポンス**: `200 OK` - `TaskCategoryResponse[]`

### POST /api/task-categories/
タスク分類を作成する。

- **権限**: admin のみ
- **リクエストボディ**: `TaskCategoryCreate`

| フィールド | 型 | 必須 | 説明 |
|------------|-----|------|------|
| name | string | Yes | カテゴリ名 |

- **レスポンス**: `201 Created` - `TaskCategoryResponse`

### PUT /api/task-categories/{id}
タスク分類を更新する。

- **権限**: admin のみ
- **レスポンス**: `200 OK` - `TaskCategoryResponse`
- **エラー**: `404 Not Found`

### DELETE /api/task-categories/{id}
タスク分類を削除する。

- **権限**: admin のみ
- **レスポンス**: `204 No Content`
- **エラー**: `404 Not Found`

### TaskCategoryResponse スキーマ

| フィールド | 型 | 説明 |
|------------|-----|------|
| id | integer | カテゴリID |
| name | string | カテゴリ名 |

---

## 9. Log API (`/api/logs`)

### POST /api/logs/
ログを登録する。登録後、WebSocket経由で全接続クライアントにブロードキャストされる。アラートルール評価も実行される。

- **権限**: 認証不要
- **リクエストボディ**: `LogCreate`

| フィールド | 型 | 必須 | デフォルト | 説明 |
|------------|-----|------|-----------|------|
| system_name | string | Yes | - | システム名 |
| log_type | string | Yes | - | ログ種別 |
| severity | string | No | "INFO" | 重要度 |
| message | string | Yes | - | メッセージ |
| extra_data | any | No | null | 追加データ (JSON) |

- **レスポンス**: `201 Created` - `LogResponse`

### GET /api/logs/
ログ一覧を受信日時降順で取得する。

- **クエリパラメータ**: `limit` (integer, デフォルト 100)
- **レスポンス**: `200 OK` - `LogResponse[]`

### GET /api/logs/important
重要ログ（severity が WARNING, ERROR, CRITICAL のいずれか）の一覧を取得する。

- **クエリパラメータ**: `limit` (integer, デフォルト 100)
- **レスポンス**: `200 OK` - `LogResponse[]`

### LogResponse スキーマ

| フィールド | 型 | 説明 |
|------------|-----|------|
| id | integer | ログID |
| system_name | string | システム名 |
| log_type | string | ログ種別 |
| severity | string | 重要度 |
| message | string | メッセージ |
| extra_data | any \| null | 追加データ |
| received_at | datetime | 受信日時 |

---

## 10. User API (`/api/users`)

### GET /api/users/
ユーザー一覧を取得する。

- **権限**: 認証済みユーザー
- **レスポンス**: `200 OK` - `UserResponse[]`

### POST /api/users/
新しいユーザーを作成する。

- **権限**: admin のみ
- **リクエストボディ**: `UserCreate`

| フィールド | 型 | 必須 | デフォルト | 説明 |
|------------|-----|------|-----------|------|
| email | string (EmailStr) | Yes | - | メールアドレス |
| display_name | string | Yes | - | 表示名 |
| password | string | Yes | - | パスワード |
| role | string | No | "user" | ロール (admin/user) |

- **レスポンス**: `201 Created` - `UserResponse`
- **エラー**: `400 Bad Request` - メールアドレス重複

### GET /api/users/{user_id}
指定IDのユーザーを取得する。

- **権限**: 認証済みユーザー
- **レスポンス**: `200 OK` - `UserResponse`
- **エラー**: `404 Not Found`

### PUT /api/users/{user_id}
ユーザー情報を更新する。

- **権限**: admin は全ユーザー編集可（ただし自分の role/is_active は変更不可）。一般ユーザーは自分の display_name のみ編集可。
- **リクエストボディ**: `UserUpdate`

| フィールド | 型 | 必須 | 説明 |
|------------|-----|------|------|
| display_name | string | No | 表示名 |
| email | string (EmailStr) | No | メールアドレス（admin のみ） |
| role | string | No | ロール（admin のみ） |
| is_active | boolean | No | 有効フラグ（admin のみ） |
| group_id | integer | No | 所属グループID（admin のみ） |
| preferred_locale | string | No | 優先ロケール（"ja"/"en"、全ユーザー変更可） |

- **レスポンス**: `200 OK` - `UserResponse`
- **エラー**: `403 Forbidden` / `404 Not Found`

### DELETE /api/users/{user_id}
ユーザーを削除する。

- **権限**: admin のみ（自分自身の削除は不可）
- **レスポンス**: `204 No Content`
- **エラー**: `403 Forbidden` / `404 Not Found`

### PUT /api/users/me/password
自分のパスワードを変更する。

- **リクエストボディ**: `PasswordChange`

| フィールド | 型 | 必須 | 説明 |
|------------|-----|------|------|
| current_password | string | Yes | 現在のパスワード |
| new_password | string | Yes | 新しいパスワード |

- **レスポンス**: `200 OK` - `{"detail": "Password changed"}`
- **エラー**: `400 Bad Request` - 現在のパスワード不一致

### PUT /api/users/{user_id}/password
パスワードを強制リセットする。

- **権限**: admin のみ
- **リクエストボディ**: `PasswordReset`

| フィールド | 型 | 必須 | 説明 |
|------------|-----|------|------|
| new_password | string | Yes | 新しいパスワード |

- **レスポンス**: `200 OK` - `{"detail": "Password reset"}`

### POST /api/users/{user_id}/unlock
アカウントロックを解除する。

- **権限**: admin のみ
- **レスポンス**: `200 OK` - `{"detail": "Account unlocked"}`
- **エラー**: `404 Not Found`

### UserResponse スキーマ

| フィールド | 型 | 説明 |
|------------|-----|------|
| id | integer | ユーザーID |
| email | string | メールアドレス |
| display_name | string | 表示名 |
| role | string | ロール (admin/user) |
| is_active | boolean | 有効フラグ |
| group_id | integer \| null | 所属グループID |
| group_name | string \| null | 所属グループ名 |
| created_at | datetime | 作成日時 |
| updated_at | datetime \| null | 更新日時 |

---

## 11. Presence API (`/api/presence`)

### PUT /api/presence/status
自分の在籍ステータスを更新する。更新後、WebSocket経由で全接続クライアントにブロードキャストされる。

- **リクエストボディ**: `PresenceUpdateRequest`

| フィールド | 型 | 必須 | 説明 |
|------------|-----|------|------|
| status | string | Yes | ステータス ("available" / "away" / "out" / "break" / "offline" / "meeting" / "remote") |
| message | string | No | ステータスメッセージ |

- **レスポンス**: `200 OK` - `PresenceStatusResponse`

### GET /api/presence/statuses
アクティブユーザーの在籍状態一覧を取得する（display_name付き）。ステータスが未設定のユーザーは "offline" として表示される。is_active=false のユーザーは除外される。

- **レスポンス**: `200 OK` - `PresenceStatusWithUser[]`

### GET /api/presence/me
自分の在籍状態を取得する。

- **レスポンス**: `200 OK` - `PresenceStatusResponse`

### GET /api/presence/logs
自分の在籍状態変更履歴を取得する。

- **レスポンス**: `200 OK` - `PresenceLogResponse[]`

### PresenceStatusResponse スキーマ

| フィールド | 型 | 説明 |
|------------|-----|------|
| id | integer | ステータスID |
| user_id | integer | ユーザーID |
| status | string | 在籍ステータス |
| message | string \| null | ステータスメッセージ |
| updated_at | datetime \| null | 更新日時 |

### PresenceStatusWithUser スキーマ

| フィールド | 型 | 説明 |
|------------|-----|------|
| user_id | integer | ユーザーID |
| display_name | string | 表示名 |
| status | string | 在籍ステータス |
| message | string \| null | ステータスメッセージ |
| updated_at | datetime \| null | 更新日時 |
| active_tickets | ActiveTicket[] | 作業中タスクのBacklogチケット一覧 |

### ActiveTicket スキーマ

| フィールド | 型 | 説明 |
|------------|-----|------|
| task_id | integer | タスクID |
| task_title | string | タスクタイトル |
| backlog_ticket_id | string | Backlogチケット番号 |

---

## 12. Report API (`/api/reports`)

### GET /api/reports/
自分の日報一覧を取得する。

- **レスポンス**: `200 OK` - `DailyReportResponse[]`

### GET /api/reports/all
全ユーザーの日報一覧を取得する。

- **レスポンス**: `200 OK` - `DailyReportResponse[]`

### POST /api/reports/
日報を作成する。同一ユーザー・同一日に複数件の作成が可能。

- **リクエストボディ**: `DailyReportCreate`

| フィールド | 型 | 必須 | 説明 |
|------------|-----|------|------|
| report_date | date | Yes | 対象日 |
| category_id | integer | Yes | タスク分類ID |
| task_name | string | Yes | タスク名 |
| backlog_ticket_id | string | No | Backlogチケット番号（例: WHT-488） |
| time_minutes | integer | No (default 0) | 作業時間（分） |
| work_content | string | Yes | 業務内容 |
| achievements | string | No | 成果・進捗 |
| issues | string | No | 課題・問題 |
| next_plan | string | No | 明日の予定 |
| remarks | string | No | 備考 |

- **レスポンス**: `201 Created` - `DailyReportResponse`

### GET /api/reports/{report_id}
日報を取得する（全認証ユーザーが閲覧可能）。

- **レスポンス**: `200 OK` - `DailyReportResponse`
- **エラー**: `404 Not Found`

### PUT /api/reports/{report_id}
日報を更新する（所有者のみ）。

- **リクエストボディ**: `DailyReportUpdate`（全フィールド任意、category_id/task_name/backlog_ticket_id/time_minutes含む）
- **レスポンス**: `200 OK` - `DailyReportResponse`
- **エラー**: `404 Not Found`

### DELETE /api/reports/{report_id}
日報を削除する（所有者のみ）。

- **レスポンス**: `204 No Content`
- **エラー**: `404 Not Found`

### DailyReportResponse スキーマ

| フィールド | 型 | 説明 |
|------------|-----|------|
| id | integer | 日報ID |
| user_id | integer | ユーザーID |
| report_date | date | 対象日 |
| category_id | integer | タスク分類ID |
| task_name | string | タスク名 |
| backlog_ticket_id | string \| null | Backlogチケット番号 |
| time_minutes | integer | 作業時間（分） |
| work_content | string | 業務内容 |
| achievements | string \| null | 成果・進捗 |
| issues | string \| null | 課題・問題 |
| next_plan | string \| null | 明日の予定 |
| remarks | string \| null | 備考 |
| created_at | datetime | 作成日時 |
| updated_at | datetime \| null | 更新日時 |

---

## 13. Summary API (`/api/summary`)

### GET /api/summary/
業務サマリーを取得する。

- **クエリパラメータ**:

| パラメータ | 型 | デフォルト | 説明 |
|------------|-----|-----------|------|
| period | string | "weekly" | 期間 ("daily" / "weekly" / "monthly") |
| ref_date | date | 当日 | 基準日 |
| group_id | integer | null | グループIDフィルタ（任意） |

- **レスポンス**: `200 OK` - `BusinessSummaryResponse`

### BusinessSummaryResponse スキーマ

| フィールド | 型 | 説明 |
|------------|-----|------|
| period_start | date | 期間開始日 |
| period_end | date | 期間終了日 |
| period | string | 期間種別 ("daily" / "weekly" / "monthly") |
| total_reports | integer | 日報件数 |
| user_report_statuses | array | ユーザーごとの日報提出状況 |
| report_trends | array | 日付ごとの日報件数推移 |
| category_trends | CategoryTrend[] | タスク分類別の作業時間・件数集計 |
| categories | array | タスク分類マスタ一覧 |
| recent_reports | array | 直近の日報一覧 |
| issues | array | 課題・問題の集約 |

### CategoryTrend スキーマ

| フィールド | 型 | 説明 |
|------------|-----|------|
| category_id | integer | タスク分類ID |
| category_name | string | タスク分類名 |
| report_count | integer | 日報件数 |
| total_minutes | integer | 合計作業時間（分） |

---

## 14. Log Source API (`/api/log-sources`)

### GET /api/log-sources/
ログソース一覧を取得する。

- **レスポンス**: `200 OK` - `LogSourceResponse[]`

### GET /api/log-sources/status
ログソースのステータス一覧を取得する（ダッシュボードカード用軽量レスポンス）。

- **レスポンス**: `200 OK` - `LogSourceStatusResponse[]`

### POST /api/log-sources/
ログソースを作成する。

- **権限**: admin のみ
- **リクエストボディ**: `LogSourceCreate`

| フィールド | 型 | 必須 | デフォルト | 説明 |
|------------|-----|------|-----------|------|
| name | string | Yes | - | ソース名 |
| group_id | integer | Yes | - | グループID |
| access_method | string | Yes | - | 接続方式（"ftp" または "smb"） |
| host | string | Yes | - | 接続先ホスト名/IP |
| port | integer | No | null | ポート番号（未指定時はプロトコルデフォルト） |
| username | string | Yes | - | 接続ユーザー名 |
| password | string | Yes | - | 接続パスワード |
| domain | string | No | null | ドメイン名（SMB のみ） |
| paths | LogSourcePathCreate[] | Yes | - | 監視パスリスト（1件以上必須） |
| encoding | string | No | "utf-8" | ファイルエンコーディング |
| source_type | string | No | "OTHER" | ソース種別（WEB/HT/BATCH/OTHER） |
| polling_interval_sec | integer | No | 60 | ポーリング間隔（秒、60〜3600） |
| collection_mode | string | No | "metadata_only" | 収集モード（metadata_only/full_import） |
| parser_pattern | string | No | null | 正規表現（名前付きグループ） |
| severity_field | string | No | null | severity を抽出するグループ名 |
| default_severity | string | No | "INFO" | severity 未抽出時のデフォルト |
| is_enabled | boolean | No | true | 有効/無効 |
| alert_on_change | boolean | No | false | ファイル変更時アラートフラグ |

- **レスポンス**: `201 Created` - `LogSourceResponse`
- **エラー**: `422 Unprocessable Entity` - 不正な正規表現 / polling_interval_sec 範囲外 / 不正な access_method / 不正な source_type / 不正な collection_mode

### GET /api/log-sources/{id}
ログソースを取得する。

- **レスポンス**: `200 OK` - `LogSourceResponse`
- **エラー**: `404 Not Found`

### PUT /api/log-sources/{id}
ログソースを更新する。指定されたフィールドのみ更新。

- **権限**: admin のみ
- **リクエストボディ**: `LogSourceUpdate`（全フィールド任意、alert_on_change含む）
- **レスポンス**: `200 OK` - `LogSourceResponse`
- **エラー**: `404 Not Found`

### DELETE /api/log-sources/{id}
ログソースを削除する。

- **権限**: admin のみ
- **レスポンス**: `204 No Content`
- **エラー**: `404 Not Found`

### POST /api/log-sources/{id}/test
ログソースへの接続テストを実行する。リモートサーバーに接続し、各パスの配下のファイル一覧取得を試みる。パスごとの結果を返却する。

- **権限**: admin のみ
- **レスポンス**: `200 OK` - `ConnectionTestResponse`
- **エラー**: `404 Not Found`

### GET /api/log-sources/{id}/files
ログソースに紐づくファイル一覧を取得する。

- **クエリパラメータ**:

| パラメータ | 型 | デフォルト | 説明 |
|------------|-----|-----------|------|
| status | string | null | ステータスフィルタ（任意） |

- **レスポンス**: `200 OK` - `LogFileResponse[]`
- **エラー**: `404 Not Found`

### POST /api/log-sources/{id}/scan
ログソースのスキャンを実行する。リモートサーバーに接続し、当日（file_modified_at が今日）のファイルのみ登録/更新。各ファイルのタイムスタンプ変更を検出し、変更があったファイル名とフォルダパスをレスポンスに含める。alert_on_change=true の場合、変更ファイル名・フォルダパスを含むアラートを自動生成。

- **権限**: admin のみ
- **レスポンス**: `200 OK` - `ScanResultResponse`
- **エラー**: `404 Not Found`

### POST /api/log-sources/{id}/re-read
ログソースのコンテンツを再読込する。既存の `log_entries` を全削除し、`last_read_line` を 0 にリセットした後、スキャンを再実行する。エンコーディング変更後などにコンテンツを正しく再取得する際に使用する。

- **権限**: admin のみ
- **レスポンス**: `200 OK` - `ScanResultResponse`
- **エラー**: `404 Not Found`

### ScanResultResponse スキーマ

| フィールド | 型 | 説明 |
|------------|-----|------|
| file_count | integer | 対象ファイル数 |
| new_count | integer | 新規ファイル数 |
| updated_count | integer | 更新ファイル数 |
| alerts_created | integer | 作成されたアラート数 |
| message | string | 結果メッセージ |
| changed_paths | ChangedPathInfo[] | 変更があったパスごとの詳細（フォルダリンク・変更ファイル名含む） |
| content_read_files | integer | コンテンツ読み込みを行ったファイル数（alert_on_change時のみ） |

### ChangedPathInfo スキーマ

変更が検出されたパスの詳細情報。フォルダリンクと変更ファイル名を含む。

| フィールド | 型 | 説明 |
|------------|-----|------|
| path_id | integer | パスID |
| base_path | string | ベースディレクトリパス |
| folder_link | string | フォルダリンクURL（SMB: `file://///host/path/`、FTP: `ftp://host:port/path/`） |
| copy_path | string | クリップボードコピー用パス（SMB: `\\host\share\path\`、FTP: `ftp://host:port/path/`） |
| new_files | string[] | 新規検出ファイル名リスト |
| updated_files | string[] | タイムスタンプ更新ファイル名リスト |

### LogSourcePathCreate スキーマ

| フィールド | 型 | 必須 | デフォルト | 説明 |
|------------|-----|------|-----------|------|
| base_path | string | Yes | - | ベースディレクトリパス |
| file_pattern | string | No | "*.log" | ファイル名パターン（glob形式） |
| is_enabled | boolean | No | true | 有効/無効 |

### LogSourcePathUpdate スキーマ

| フィールド | 型 | 必須 | 説明 |
|------------|-----|------|------|
| id | integer | No | パスID（指定時: 更新、未指定: 新規作成） |
| base_path | string | Yes | ベースディレクトリパス |
| file_pattern | string | No | ファイル名パターン（glob形式） |
| is_enabled | boolean | No | 有効/無効 |

### LogSourcePathResponse スキーマ

| フィールド | 型 | 説明 |
|------------|-----|------|
| id | integer | パスID |
| source_id | integer | ソースID |
| base_path | string | ベースディレクトリパス |
| file_pattern | string | ファイル名パターン |
| is_enabled | boolean | 有効フラグ |
| created_at | datetime | 作成日時 |
| updated_at | datetime | 更新日時 |

### LogSourceResponse スキーマ

| フィールド | 型 | 説明 |
|------------|-----|------|
| id | integer | ソースID |
| name | string | ソース名 |
| group_id | integer | グループID |
| group_name | string | グループ名 |
| access_method | string | 接続方式（ftp/smb） |
| host | string | 接続先ホスト名/IP |
| port | integer \| null | ポート番号 |
| username_masked | string | マスク済みユーザー名（表示用） |
| domain | string \| null | ドメイン名（SMB のみ） |
| paths | LogSourcePathResponse[] | 監視パスリスト |
| encoding | string | ファイルエンコーディング |
| source_type | string | ソース種別（WEB/HT/BATCH/OTHER） |
| polling_interval_sec | integer | ポーリング間隔（秒） |
| collection_mode | string | 収集モード（metadata_only/full_import） |
| parser_pattern | string \| null | 正規表現パターン |
| severity_field | string \| null | severity グループ名 |
| default_severity | string | デフォルト severity |
| is_enabled | boolean | 有効フラグ |
| alert_on_change | boolean | ファイル変更時アラートフラグ |
| consecutive_errors | integer | 連続エラー回数 |
| last_checked_at | datetime \| null | 最終チェック日時 |
| last_error | string \| null | 最終エラー |
| created_at | datetime | 作成日時 |
| updated_at | datetime | 更新日時 |

### LogSourceStatusResponse スキーマ

ダッシュボードテーブル表示用レスポンス。`has_alert=true` の場合、変更ファイルの詳細とフォルダリンクを `changed_paths` に含める。

| フィールド | 型 | 説明 |
|------------|-----|------|
| id | integer | ソースID |
| name | string | ソース名 |
| group_id | integer | グループID |
| group_name | string | グループ名 |
| access_method | string | 接続方式（ftp/smb） |
| host | string | 接続先ホスト名/IP |
| source_type | string | ソース種別 |
| collection_mode | string | 収集モード |
| is_enabled | boolean | 有効フラグ |
| alert_on_change | boolean | ファイル変更通知フラグ |
| consecutive_errors | integer | 連続エラー回数 |
| last_checked_at | datetime \| null | 最終チェック日時 |
| last_error | string \| null | 最終エラー |
| path_count | integer | 監視パス数 |
| file_count | integer | 管理対象ファイル数 |
| new_file_count | integer | 新規ファイル数 |
| updated_file_count | integer | 更新ファイル数 |
| has_alert | boolean | アラート状態（alert_on_change AND is_enabled AND 変更ファイルあり） |
| changed_paths | ChangedPathInfo[] | 変更があったパスの詳細（has_alert=true時のみ値あり、false時は空配列） |

### PathTestResult スキーマ

| フィールド | 型 | 説明 |
|------------|-----|------|
| base_path | string | テスト対象パス |
| file_pattern | string | ファイルパターン |
| status | string | テスト結果（"ok" または "error"） |
| file_count | integer | 検出ファイル数 |
| message | string | 結果メッセージ |

### ConnectionTestResponse スキーマ

| フィールド | 型 | 説明 |
|------------|-----|------|
| status | string | テスト結果（"ok" または "error"） |
| file_count | integer | 検出ファイル数（全パス合計） |
| message | string | 結果メッセージ |
| path_results | PathTestResult[] | パスごとのテスト結果 |

### LogFileResponse スキーマ

| フィールド | 型 | 説明 |
|------------|-----|------|
| id | integer | ファイルID |
| source_id | integer | ソースID |
| path_id | integer | パスID |
| file_name | string | ファイル名 |
| file_size | integer | ファイルサイズ（バイト） |
| file_modified_at | datetime \| null | ファイル更新日時 |
| last_read_line | integer | 最終読取行番号 |
| status | string | ステータス |
| created_at | datetime | 作成日時 |
| updated_at | datetime | 更新日時 |

---

## 15. Alert API (`/api/alerts`)

### GET /api/alerts/
アラート一覧を取得する。

- **クエリパラメータ**:

| パラメータ | 型 | デフォルト | 説明 |
|------------|-----|-----------|------|
| active_only | boolean | false | アクティブなアラートのみ取得 |
| limit | integer | 100 | 取得件数上限 |

- **レスポンス**: `200 OK` - `AlertResponse[]`

### GET /api/alerts/count
未確認アラート件数を取得する（ナビバッジ用）。

- **レスポンス**: `200 OK` - `AlertCountResponse`

| フィールド | 型 | 説明 |
|------------|-----|------|
| count | integer | 未確認アラート件数 |

### POST /api/alerts/
手動アラートを作成する。

- **リクエストボディ**: `AlertCreate`

| フィールド | 型 | 必須 | デフォルト | 説明 |
|------------|-----|------|-----------|------|
| title | string | Yes | - | アラートタイトル |
| message | string | Yes | - | アラートメッセージ |
| severity | string | No | "info" | 重要度 (critical/warning/info) |
| source | string | No | null | アラートソース |

- **レスポンス**: `201 Created` - `AlertResponse`

### GET /api/alerts/{id}
アラートを取得する。

- **レスポンス**: `200 OK` - `AlertResponse`
- **エラー**: `404 Not Found`

### PATCH /api/alerts/{id}/acknowledge
アラートを確認済みにする。確認者のuser_idと日時が記録される。

- **レスポンス**: `200 OK` - `AlertResponse`
- **エラー**: `404 Not Found`

### PATCH /api/alerts/{id}/deactivate
アラートを非アクティブにする。

- **レスポンス**: `200 OK` - `AlertResponse`
- **エラー**: `404 Not Found`

### DELETE /api/alerts/{id}
アラートを削除する。

- **権限**: admin のみ
- **レスポンス**: `204 No Content`
- **エラー**: `404 Not Found`

### AlertResponse スキーマ

| フィールド | 型 | 説明 |
|------------|-----|------|
| id | integer | アラートID |
| title | string | タイトル |
| message | string | メッセージ |
| severity | string | 重要度 (critical/warning/info) |
| source | string \| null | アラートソース |
| rule_id | integer \| null | 自動生成元ルールID |
| is_active | boolean | アクティブフラグ |
| acknowledged | boolean | 確認済みフラグ |
| acknowledged_by | integer \| null | 確認者user_id |
| acknowledged_at | datetime \| null | 確認日時 |
| created_at | datetime | 発生日時 |

---

## 16. Alert Rule API (`/api/alert-rules`)

### GET /api/alert-rules/
アラートルール一覧を取得する。

- **レスポンス**: `200 OK` - `AlertRuleResponse[]`

### POST /api/alert-rules/
アラートルールを作成する。

- **権限**: admin のみ
- **リクエストボディ**: `AlertRuleCreate`

| フィールド | 型 | 必須 | デフォルト | 説明 |
|------------|-----|------|-----------|------|
| name | string | Yes | - | ルール名 |
| condition | object | Yes | - | マッチ条件（JSON） |
| alert_title_template | string | Yes | - | タイトルテンプレート |
| alert_message_template | string | No | null | メッセージテンプレート |
| severity | string | No | "warning" | 生成アラートの重要度 |
| is_enabled | boolean | No | true | ルール有効/無効 |

**condition の書式**:
- 完全一致: `{"severity": "ERROR"}`
- リスト包含: `{"severity": {"$in": ["ERROR", "CRITICAL"]}}`
- 部分一致: `{"message": {"$contains": "database"}}`
- 複合条件（AND）: `{"severity": "ERROR", "system_name": "prod"}`

- **レスポンス**: `201 Created` - `AlertRuleResponse`

### GET /api/alert-rules/{id}
アラートルールを取得する。

- **レスポンス**: `200 OK` - `AlertRuleResponse`
- **エラー**: `404 Not Found`

### PUT /api/alert-rules/{id}
アラートルールを更新する。指定されたフィールドのみ更新。

- **権限**: admin のみ
- **リクエストボディ**: `AlertRuleUpdate`（全フィールド任意）
- **レスポンス**: `200 OK` - `AlertRuleResponse`
- **エラー**: `404 Not Found`

### DELETE /api/alert-rules/{id}
アラートルールを削除する。

- **権限**: admin のみ
- **レスポンス**: `204 No Content`
- **エラー**: `404 Not Found`

### AlertRuleResponse スキーマ

| フィールド | 型 | 説明 |
|------------|-----|------|
| id | integer | ルールID |
| name | string | ルール名 |
| condition | object | マッチ条件（JSON） |
| alert_title_template | string | タイトルテンプレート |
| alert_message_template | string \| null | メッセージテンプレート |
| severity | string | 生成アラートの重要度 |
| is_enabled | boolean | ルール有効/無効 |
| created_at | datetime | 作成日時 |
| updated_at | datetime | 更新日時 |

---

## 17. Attendance Preset API (`/api/attendance-presets`)

### GET /api/attendance-presets/
出勤プリセット一覧を取得する。

- **レスポンス**: `200 OK` - `AttendancePresetResponse[]`

### AttendancePresetResponse スキーマ

| フィールド | 型 | 説明 |
|------------|-----|------|
| id | integer | プリセットID |
| name | string | プリセット名 |
| clock_in | string | 出勤時刻（HH:MM） |
| clock_out | string | 退勤時刻（HH:MM） |
| break_start | string \| null | 休憩開始時刻（HH:MM） |
| break_end | string \| null | 休憩終了時刻（HH:MM） |

---

## 18. Site Link API (`/api/sites`)

### GET /api/sites/
サイトリンク一覧を取得する。

- **レスポンス**: `200 OK` - `SiteLinkResponse[]`

### POST /api/sites/
サイトリンクを作成する。

- **リクエストボディ**: `SiteLinkCreate`

| フィールド | 型 | 必須 | デフォルト | 説明 |
|------------|-----|------|-----------|------|
| name | string | Yes | - | サイト名 |
| url | string | Yes | - | URL（http:// または https://） |
| description | string | No | null | 説明 |
| group_id | integer | No | null | サイトグループID |
| sort_order | integer | No | 0 | 表示順 |
| is_enabled | boolean | No | true | 有効/無効 |
| check_enabled | boolean | No | true | ヘルスチェック有効/無効 |
| check_interval_sec | integer | No | 300 | チェック間隔（秒、60〜3600） |
| check_timeout_sec | integer | No | 10 | タイムアウト（秒、3〜60） |
| check_ssl_verify | boolean | No | true | SSL証明書検証 |

- **レスポンス**: `201 Created` - `SiteLinkResponse`

### GET /api/sites/{id}
サイトリンクを取得する。

- **レスポンス**: `200 OK` - `SiteLinkResponse`
- **エラー**: `404 Not Found`

### GET /api/sites/{id}/url
サイトリンクのURLを取得する。URL保護用（一覧レスポンスにはURLを含まない）。

- **レスポンス**: `200 OK` - `SiteUrlResponse`
- **エラー**: `404 Not Found`

### PUT /api/sites/{id}
サイトリンクを更新する。

- **権限**: 作成者のみ
- **リクエストボディ**: `SiteLinkUpdate`（全フィールド任意）
- **レスポンス**: `200 OK` - `SiteLinkResponse`
- **エラー**: `403 Forbidden` / `404 Not Found`

### DELETE /api/sites/{id}
サイトリンクを削除する。

- **権限**: 作成者のみ
- **レスポンス**: `204 No Content`
- **エラー**: `403 Forbidden` / `404 Not Found`

### POST /api/sites/{id}/check
サイトリンクのヘルスチェックを手動実行する。

- **レスポンス**: `200 OK` - `SiteCheckResponse`
- **エラー**: `404 Not Found`

### SiteLinkResponse スキーマ

| フィールド | 型 | 説明 |
|------------|-----|------|
| id | integer | サイトリンクID |
| name | string | サイト名 |
| description | string \| null | 説明 |
| group_id | integer \| null | サイトグループID |
| group_name | string \| null | サイトグループ名 |
| created_by | integer \| null | 作成者ID |
| sort_order | integer | 表示順 |
| is_enabled | boolean | 有効フラグ |
| check_enabled | boolean | ヘルスチェック有効フラグ |
| check_interval_sec | integer | チェック間隔（秒） |
| check_timeout_sec | integer | タイムアウト（秒） |
| check_ssl_verify | boolean | SSL証明書検証フラグ |
| status | string | ステータス（unknown/healthy/unhealthy/error） |
| response_time_ms | integer \| null | レスポンス時間（ミリ秒） |
| http_status_code | integer \| null | HTTPステータスコード |
| last_checked_at | datetime \| null | 最終チェック日時 |
| last_status_changed_at | datetime \| null | 最終ステータス変更日時 |
| consecutive_failures | integer | 連続失敗回数 |
| last_error | string \| null | 最終エラー |
| created_at | datetime | 作成日時 |
| updated_at | datetime \| null | 更新日時 |

### SiteUrlResponse スキーマ

| フィールド | 型 | 説明 |
|------------|-----|------|
| id | integer | サイトリンクID |
| url | string | URL |

### SiteCheckResponse スキーマ

| フィールド | 型 | 説明 |
|------------|-----|------|
| id | integer | サイトリンクID |
| status | string | チェック後のステータス |
| previous_status | string | チェック前のステータス |
| response_time_ms | integer \| null | レスポンス時間（ミリ秒） |
| http_status_code | integer \| null | HTTPステータスコード |
| checked_at | datetime | チェック日時 |
| message | string | 結果メッセージ |

---

## 19. Site Group API (`/api/site-groups`)

### GET /api/site-groups/
サイトグループ一覧を取得する。

- **レスポンス**: `200 OK` - `SiteGroupResponse[]`

### POST /api/site-groups/
サイトグループを作成する。

- **権限**: admin のみ
- **リクエストボディ**: `SiteGroupCreate`

| フィールド | 型 | 必須 | デフォルト | 説明 |
|------------|-----|------|-----------|------|
| name | string | Yes | - | グループ名 |
| description | string | No | null | 説明 |
| color | string | No | "#6c757d" | 表示色（#RRGGBB形式） |
| icon | string | No | null | アイコン |
| sort_order | integer | No | 0 | 表示順 |

- **レスポンス**: `201 Created` - `SiteGroupResponse`

### PUT /api/site-groups/{id}
サイトグループを更新する。

- **権限**: admin のみ
- **リクエストボディ**: `SiteGroupUpdate`（全フィールド任意）
- **レスポンス**: `200 OK` - `SiteGroupResponse`
- **エラー**: `404 Not Found`

### DELETE /api/site-groups/{id}
サイトグループを削除する。

- **権限**: admin のみ
- **レスポンス**: `204 No Content`
- **エラー**: `404 Not Found`

### SiteGroupResponse スキーマ

| フィールド | 型 | 説明 |
|------------|-----|------|
| id | integer | グループID |
| name | string | グループ名 |
| description | string \| null | 説明 |
| color | string | 表示色 |
| icon | string \| null | アイコン |
| sort_order | integer | 表示順 |
| link_count | integer | 所属リンク数 |

---

## 20. WebSocket

接続管理・認証・再接続の共通仕様は [spec_nonfunction.md](./spec_nonfunction.md) セクション5 を参照。

| エンドポイント | トリガー | ブロードキャスト内容 |
|---------------|---------|-------------------|
| `/ws/logs` | `POST /api/logs/` | ログデータ（JSON） |
| `/ws/presence` | `PUT /api/presence/status` | ステータスデータ（JSON） |
| `/ws/alerts` | アラート生成（手動 or ルール評価） | アラートデータ（JSON）+ ナビバッジ更新 |
| `/ws/sites` | サイトリンクヘルスチェック完了 | ヘルスチェック結果データ（JSON） |

---

## 21. Wiki カテゴリ API (`/api/wiki/categories`)

### GET /api/wiki/categories/
Wikiカテゴリ一覧を取得する。

- **権限**: 認証済みユーザー
- **レスポンス**: `200 OK` - `WikiCategoryResponse[]`

### POST /api/wiki/categories/
Wikiカテゴリを作成する。

- **権限**: admin のみ
- **リクエストボディ**: `WikiCategoryCreate`

| フィールド | 型 | 必須 | デフォルト | 説明 |
|------------|-----|------|-----------|------|
| name | string | Yes | - | カテゴリ名 |
| description | string | No | null | 説明 |
| color | string | No | "#6c757d" | 表示色（#RRGGBB） |
| sort_order | integer | No | 0 | 表示順 |

- **レスポンス**: `201 Created` - `WikiCategoryResponse`
- **エラー**: `400 Bad Request` - 名前重複

### PUT /api/wiki/categories/{id}
Wikiカテゴリを更新する。

- **権限**: admin のみ
- **リクエストボディ**: `WikiCategoryUpdate`（全フィールド任意）
- **レスポンス**: `200 OK` - `WikiCategoryResponse`
- **エラー**: `404 Not Found`

### DELETE /api/wiki/categories/{id}
Wikiカテゴリを削除する。

- **権限**: admin のみ
- **レスポンス**: `204 No Content`
- **エラー**: `404 Not Found`

### WikiCategoryResponse スキーマ

| フィールド | 型 | 説明 |
|------------|-----|------|
| id | integer | カテゴリID |
| name | string | カテゴリ名 |
| description | string \| null | 説明 |
| color | string | 表示色 |
| sort_order | integer | 表示順 |
| page_count | integer | 所属ページ数 |

---

## 22. Wiki タグ API (`/api/wiki/tags`)

### GET /api/wiki/tags/
Wikiタグ一覧を取得する。

- **権限**: 認証済みユーザー
- **クエリパラメータ**: `q` (string, 任意) — タグ名部分一致フィルタ
- **レスポンス**: `200 OK` - `WikiTagResponse[]`

### POST /api/wiki/tags/
Wikiタグを作成する。

- **権限**: 認証済みユーザー
- **リクエストボディ**: `WikiTagCreate`

| フィールド | 型 | 必須 | デフォルト | 説明 |
|------------|-----|------|-----------|------|
| name | string | Yes | - | タグ名 |
| color | string | No | "#6c757d" | 表示色（#RRGGBB） |

- **レスポンス**: `201 Created` - `WikiTagResponse`
- **エラー**: `400 Bad Request` - 名前重複

### DELETE /api/wiki/tags/{id}
Wikiタグを削除する。

- **権限**: admin のみ
- **レスポンス**: `204 No Content`
- **エラー**: `404 Not Found`

### WikiTagResponse スキーマ

| フィールド | 型 | 説明 |
|------------|-----|------|
| id | integer | タグID |
| name | string | タグ名 |
| slug | string | URLスラッグ |
| color | string | 表示色 |
| page_count | integer | 所属ページ数 |

---

## 23. Wiki ページ API (`/api/wiki/pages`)

### GET /api/wiki/pages/tree
Wikiページ階層ツリーを取得する。

- **権限**: 認証済みユーザー
- **レスポンス**: `200 OK` - `WikiPageTreeNode[]`

### GET /api/wiki/pages/by-slug/{slug}
スラッグ指定でWikiページを取得する（パンくずリスト・本文付き）。

- **権限**: 認証済みユーザー
- **レスポンス**: `200 OK` - `WikiPageDetailResponse`
- **エラー**: `404 Not Found`

### GET /api/wiki/pages/
Wikiページ一覧を取得する。

- **権限**: 認証済みユーザー
- **クエリパラメータ**:

| パラメータ | 型 | デフォルト | 説明 |
|------------|-----|-----------|------|
| tag_slug | string | null | タグスラッグフィルタ |
| category_id | integer | null | カテゴリIDフィルタ |

- **レスポンス**: `200 OK` - `WikiPageResponse[]`

### POST /api/wiki/pages/
Wikiページを作成する。

- **権限**: 認証済みユーザー
- **リクエストボディ**: `WikiPageCreate`

| フィールド | 型 | 必須 | デフォルト | 説明 |
|------------|-----|------|-----------|------|
| title | string | Yes | - | ページタイトル |
| slug | string | No | 自動生成 | URLスラッグ（重複時はサフィックス付与） |
| parent_id | integer | No | null | 親ページID |
| content | string | No | "" | 本文（Markdown） |
| sort_order | integer | No | 0 | 表示順 |
| visibility | string | No | "local" | 公開範囲 (local/public/private) |
| category_id | integer | No | null | カテゴリID |
| tag_ids | integer[] | No | [] | タグIDリスト |

- **レスポンス**: `201 Created` - `WikiPageDetailResponse`

### GET /api/wiki/pages/{id}
IDでWikiページを取得する（パンくずリスト・本文付き）。

- **権限**: 認証済みユーザー
- **レスポンス**: `200 OK` - `WikiPageDetailResponse`
- **エラー**: `404 Not Found`

### PUT /api/wiki/pages/{id}
Wikiページを更新する（作成者のみ）。

- **権限**: 作成者のみ
- **リクエストボディ**: `WikiPageUpdate`（全フィールド任意）

| フィールド | 型 | 必須 | 説明 |
|------------|-----|------|------|
| title | string | No | タイトル |
| slug | string | No | スラッグ |
| content | string | No | 本文（Markdown） |
| sort_order | integer | No | 表示順 |
| visibility | string | No | 公開範囲 |
| category_id | integer | No | カテゴリID |

- **レスポンス**: `200 OK` - `WikiPageDetailResponse`
- **エラー**: `403 Forbidden` / `404 Not Found`

### DELETE /api/wiki/pages/{id}
Wikiページを削除する（作成者のみ）。

- **権限**: 作成者のみ
- **レスポンス**: `204 No Content`
- **エラー**: `403 Forbidden` / `404 Not Found`

### PUT /api/wiki/pages/{id}/move
Wikiページを別の親の下に移動する（作成者のみ）。

- **権限**: 作成者のみ
- **リクエストボディ**: `WikiPageMove`

| フィールド | 型 | 必須 | 説明 |
|------------|-----|------|------|
| parent_id | integer \| null | No | 新しい親ページID（null=ルート） |
| sort_order | integer | No | 表示順 |

- **レスポンス**: `200 OK` - `WikiPageDetailResponse`
- **エラー**: `400 Bad Request` - 循環参照 / `403 Forbidden` / `404 Not Found`

### PUT /api/wiki/pages/{id}/tags
ページのタグ関連付けを一括更新する（作成者のみ）。

- **権限**: 作成者のみ
- **リクエストボディ**: `WikiTagIdsUpdate`

| フィールド | 型 | 必須 | 説明 |
|------------|-----|------|------|
| tag_ids | integer[] | Yes | タグIDリスト（上書き更新） |

- **レスポンス**: `200 OK` - `WikiPageDetailResponse`
- **エラー**: `403 Forbidden` / `404 Not Found`

### GET /api/wiki/pages/{id}/tasks
ページに紐づくタスクリンク一覧を取得する。

- **権限**: 認証済みユーザー
- **レスポンス**: `200 OK` - `WikiTaskLinksResponse`
- **エラー**: `404 Not Found`

### PUT /api/wiki/pages/{id}/tasks/task-items
ページに紐づくタスクリストアイテムリンクを一括更新する（作成者のみ）。

- **権限**: 作成者のみ
- **リクエストボディ**: `WikiTaskItemLinksUpdate`

| フィールド | 型 | 必須 | 説明 |
|------------|-----|------|------|
| task_item_ids | integer[] | Yes | タスクリストアイテムIDリスト（上書き更新） |

- **レスポンス**: `200 OK` - `WikiTaskLinksResponse`
- **エラー**: `403 Forbidden` / `404 Not Found`

### POST /api/wiki/pages/{id}/tasks/{task_id}
ページに進行中タスクをリンクする（作成者のみ）。

- **権限**: 作成者のみ
- **レスポンス**: `204 No Content`
- **エラー**: `403 Forbidden` / `404 Not Found`

### DELETE /api/wiki/pages/{id}/tasks/{task_id}
ページとタスクのリンクを解除する（作成者のみ）。

- **権限**: 作成者のみ
- **レスポンス**: `204 No Content`
- **エラー**: `403 Forbidden` / `404 Not Found`

### WikiPageResponse スキーマ

| フィールド | 型 | 説明 |
|------------|-----|------|
| id | integer | ページID |
| title | string | タイトル |
| slug | string | URLスラッグ |
| parent_id | integer \| null | 親ページID |
| author_id | integer \| null | 作成者ID |
| author_name | string \| null | 作成者表示名 |
| sort_order | integer | 表示順 |
| visibility | string | 公開範囲 |
| category_id | integer \| null | カテゴリID |
| category_name | string \| null | カテゴリ名 |
| category_color | string \| null | カテゴリ表示色 |
| tags | WikiTagResponse[] | タグ一覧 |
| created_at | datetime | 作成日時 |
| updated_at | datetime \| null | 更新日時 |

### WikiPageDetailResponse スキーマ（WikiPageResponse を継承）

| フィールド | 型 | 説明 |
|------------|-----|------|
| content | string | ページ本文（Markdown） |
| breadcrumbs | WikiBreadcrumb[] | パンくずリスト |

### WikiPageTreeNode スキーマ（WikiPageResponse を継承）

| フィールド | 型 | 説明 |
|------------|-----|------|
| children | WikiPageTreeNode[] | 子ページ一覧（再帰） |

### WikiBreadcrumb スキーマ

| フィールド | 型 | 説明 |
|------------|-----|------|
| id | integer | ページID |
| title | string | タイトル |
| slug | string | URLスラッグ |

### WikiTaskLinksResponse スキーマ

| フィールド | 型 | 説明 |
|------------|-----|------|
| task_items | LinkedTaskItemResponse[] | リンク済みタスクリストアイテム |
| tasks | LinkedTaskResponse[] | リンク済みタスク |

### LinkedTaskItemResponse スキーマ

| フィールド | 型 | 説明 |
|------------|-----|------|
| id | integer | タスクリストアイテムID |
| title | string | タイトル |
| status | string | ステータス |
| assignee_id | integer \| null | 担当者ID |
| assignee_name | string \| null | 担当者名 |
| backlog_ticket_id | string \| null | Backlogチケット番号 |
| scheduled_date | date \| null | 予定日 |
| linked_at | datetime | リンク作成日時 |

### LinkedTaskResponse スキーマ

| フィールド | 型 | 説明 |
|------------|-----|------|
| link_id | integer | リンクID |
| task_id | integer \| null | タスクID（タスク削除後は null） |
| title | string | タスクタイトルスナップショット |
| status | string \| null | タスクステータス |
| user_id | integer \| null | タスク所有者ID |
| display_name | string \| null | タスク所有者表示名 |
| backlog_ticket_id | string \| null | Backlogチケット番号 |
| is_completed | boolean | true = タスク削除済み |
| linked_at | datetime | リンク作成日時 |
