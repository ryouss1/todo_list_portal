## 1. エンドポイント一覧

### API エンドポイント

#### 認証 (`/api/auth`)

| メソッド | パス | 説明 | ステータスコード | 認証 |
|---------|------|------|----------------|------|
| POST | `/api/auth/login` | ログイン | 200 / 401 | 不要 |
| POST | `/api/auth/logout` | ログアウト | 204 | 不要 |
| GET | `/api/auth/me` | ログインユーザー取得 | 200 / 401 | 必要 |
| GET | `/api/auth/audit-logs` | 認証監査ログ一覧取得 | 200 | 必要（admin） |
| POST | `/api/auth/forgot-password` | パスワードリセットメール送信 | 200 | 不要 |
| POST | `/api/auth/validate-reset-token` | リセットトークン検証 | 200 | 不要 |
| POST | `/api/auth/reset-password` | パスワードリセット実行 | 200 / 400 / 404 | 不要 |
| GET | `/api/auth/oauth/providers` | 有効OAuthプロバイダ一覧 | 200 | 不要 |
| GET | `/api/auth/oauth/{provider}/authorize` | OAuth認証開始（リダイレクト） | 302 | 不要 |
| GET | `/api/auth/oauth/{provider}/callback` | OAuthコールバック処理 | 302 / 400 | 不要 |
| DELETE | `/api/auth/oauth/{provider}/unlink` | OAuthアカウントリンク解除 | 204 / 404 | 必要 |
| GET | `/api/auth/oauth/my-links` | 自分のOAuthリンク一覧 | 200 | 必要 |

#### Todo (`/api/todos`)

| メソッド | パス | 説明 | ステータスコード | 認証 |
|---------|------|------|----------------|------|
| GET | `/api/todos/` | Todo一覧取得 | 200 | 必要 |
| POST | `/api/todos/` | Todo作成 | 201 | 必要 |
| GET | `/api/todos/public` | 公開Todo一覧取得 | 200 | 必要 |
| GET | `/api/todos/{id}` | Todo詳細取得 | 200 / 404 | 必要 |
| PUT | `/api/todos/{id}` | Todo更新 | 200 / 404 | 必要 |
| DELETE | `/api/todos/{id}` | Todo削除 | 204 / 404 | 必要 |
| PATCH | `/api/todos/{id}/toggle` | Todo完了トグル | 200 / 404 | 必要 |

#### 勤怠 (`/api/attendances`)

| メソッド | パス | 説明 | ステータスコード | 認証 |
|---------|------|------|----------------|------|
| POST | `/api/attendances/clock-in` | 出勤記録 | 201 / 400 | 必要 |
| POST | `/api/attendances/clock-out` | 退勤記録 | 200 / 400 | 必要 |
| GET | `/api/attendances/status` | 出勤状態取得 | 200 | 必要 |
| GET | `/api/attendances/my-preset` | デフォルトプリセット取得 | 200 | 必要 |
| PUT | `/api/attendances/my-preset` | デフォルトプリセット設定 | 200 / 404 | 必要 |
| POST | `/api/attendances/default-set` | プリセットから当日勤怠作成 | 200 / 400 / 403 | 必要 |
| GET | `/api/attendances/export` | 月別勤怠Excelエクスポート | 200 | 必要 |
| GET | `/api/attendances/` | 出勤履歴取得（年月フィルタ対応） | 200 | 必要 |
| POST | `/api/attendances/` | 手動勤怠記録作成 | 201 / 400 | 必要 |
| GET | `/api/attendances/{id}` | 出勤記録取得 | 200 / 404 | 必要 |
| PUT | `/api/attendances/{id}` | 出勤記録更新 | 200 / 403 / 404 | 必要 |
| DELETE | `/api/attendances/{id}` | 出勤記録削除 | 204 / 403 / 404 | 必要 |
| POST | `/api/attendances/{id}/break-start` | 休憩開始 | 200 / 400 / 403 / 404 | 必要 |
| POST | `/api/attendances/{id}/break-end` | 休憩終了 | 200 / 400 / 404 | 必要 |

#### タスク (`/api/tasks`)

| メソッド | パス | 説明 | ステータスコード | 認証 |
|---------|------|------|----------------|------|
| GET | `/api/tasks/` | タスク一覧取得 | 200 | 必要 |
| POST | `/api/tasks/` | タスク作成 | 201 | 必要 |
| POST | `/api/tasks/batch-done` | タスク一括完了 | 200 | 必要 |
| GET | `/api/tasks/{id}` | タスク詳細取得 | 200 / 404 | 必要 |
| PUT | `/api/tasks/{id}` | タスク更新 | 200 / 404 | 必要 |
| DELETE | `/api/tasks/{id}` | タスク削除 | 204 / 404 | 必要 |
| POST | `/api/tasks/{id}/done` | タスク完了（日報自動生成対応） | 204 / 404 | 必要 |
| POST | `/api/tasks/{id}/start` | タイマー開始 | 200 / 400 / 404 | 必要 |
| POST | `/api/tasks/{id}/stop` | タイマー停止 | 200 / 400 / 404 | 必要 |
| GET | `/api/tasks/{id}/time-entries` | タイムエントリ一覧 | 200 / 404 | 必要 |

#### タスクリスト (`/api/task-list`)

| メソッド | パス | 説明 | ステータスコード | 認証 |
|---------|------|------|----------------|------|
| GET | `/api/task-list/unassigned` | 未割当アイテム一覧 | 200 | 必要 |
| GET | `/api/task-list/mine` | 自分の担当アイテム一覧 | 200 | 必要 |
| GET | `/api/task-list/all` | 全アイテム一覧（ユーザー/未割当フィルタ対応） | 200 | 必要 |
| POST | `/api/task-list/` | アイテム作成 | 201 | 必要 |
| GET | `/api/task-list/{id}` | アイテム取得 | 200 / 404 | 必要 |
| PUT | `/api/task-list/{id}` | アイテム更新 | 200 / 403 / 404 | 必要 |
| DELETE | `/api/task-list/{id}` | アイテム削除 | 204 / 403 / 404 | 必要 |
| GET | `/api/task-list/{id}/children` | 子アイテム一覧 | 200 / 404 | 必要 |
| POST | `/api/task-list/{id}/assign` | 担当割り当て | 200 / 403 / 404 | 必要 |
| POST | `/api/task-list/{id}/unassign` | 担当解除 | 200 / 403 / 404 | 必要 |
| POST | `/api/task-list/{id}/start` | タスク開始 | 200 / 403 / 404 | 必要 |

#### タスク分類 (`/api/task-categories`)

| メソッド | パス | 説明 | ステータスコード | 認証 |
|---------|------|------|----------------|------|
| GET | `/api/task-categories/` | タスク分類一覧取得 | 200 | 必要 |
| POST | `/api/task-categories/` | タスク分類作成 | 201 | 必要（admin） |
| PUT | `/api/task-categories/{id}` | タスク分類更新 | 200 / 404 | 必要（admin） |
| DELETE | `/api/task-categories/{id}` | タスク分類削除 | 204 / 404 | 必要（admin） |

#### ログ (`/api/logs`)

| メソッド | パス | 説明 | ステータスコード | 認証 |
|---------|------|------|----------------|------|
| POST | `/api/logs/` | ログ作成 | 201 | 不要 |
| GET | `/api/logs/` | ログ一覧取得 | 200 | 必要 |
| GET | `/api/logs/important` | 重要ログ取得 | 200 | 必要 |

#### ユーザー (`/api/users`)

| メソッド | パス | 説明 | ステータスコード | 認証 |
|---------|------|------|----------------|------|
| GET | `/api/users/` | ユーザー一覧取得 | 200 | 必要 |
| POST | `/api/users/` | ユーザー作成 | 201 / 400 | 必要（admin） |
| PUT | `/api/users/me/password` | 自分のパスワード変更 | 200 / 400 | 必要 |
| GET | `/api/users/{id}` | ユーザー取得 | 200 / 404 | 必要 |
| PUT | `/api/users/{id}` | ユーザー情報更新 | 200 / 403 / 404 | 必要 |
| DELETE | `/api/users/{id}` | ユーザー削除 | 204 / 403 / 404 | 必要（admin） |
| PUT | `/api/users/{id}/password` | パスワード強制リセット | 200 | 必要（admin） |
| POST | `/api/users/{id}/unlock` | アカウントアンロック | 200 / 404 | 必要（admin） |

#### グループ (`/api/groups`)

| メソッド | パス | 説明 | ステータスコード | 認証 |
|---------|------|------|----------------|------|
| GET | `/api/groups/` | グループ一覧取得 | 200 | 必要 |
| POST | `/api/groups/` | グループ作成 | 201 / 400 | 必要（admin） |
| PUT | `/api/groups/{id}` | グループ更新 | 200 / 400 / 404 | 必要（admin） |
| DELETE | `/api/groups/{id}` | グループ削除 | 204 / 404 | 必要（admin） |

#### 在籍 (`/api/presence`)

| メソッド | パス | 説明 | ステータスコード | 認証 |
|---------|------|------|----------------|------|
| PUT | `/api/presence/status` | 在籍ステータス更新 | 200 | 必要 |
| GET | `/api/presence/statuses` | 全ユーザー在籍状態一覧 | 200 | 必要 |
| GET | `/api/presence/me` | 自分の在籍状態取得 | 200 | 必要 |
| GET | `/api/presence/logs` | 在籍変更履歴取得 | 200 | 必要 |

#### 日報 (`/api/reports`)

| メソッド | パス | 説明 | ステータスコード | 認証 |
|---------|------|------|----------------|------|
| GET | `/api/reports/` | 自分の日報一覧 | 200 | 必要 |
| GET | `/api/reports/all` | 全ユーザー日報一覧 | 200 | 必要 |
| POST | `/api/reports/` | 日報作成 | 201 / 400 | 必要 |
| GET | `/api/reports/{id}` | 日報詳細取得 | 200 / 404 | 必要 |
| PUT | `/api/reports/{id}` | 日報更新 | 200 / 404 | 必要 |
| DELETE | `/api/reports/{id}` | 日報削除 | 204 / 404 | 必要 |

#### 業務サマリー (`/api/summary`)

| メソッド | パス | 説明 | ステータスコード | 認証 |
|---------|------|------|----------------|------|
| GET | `/api/summary/` | 業務サマリー取得（daily/weekly/monthly、group_idフィルタ対応） | 200 / 422 | 必要 |

#### ログソース (`/api/log-sources`)

| メソッド | パス | 説明 | ステータスコード | 認証 |
|---------|------|------|----------------|------|
| GET | `/api/log-sources/` | ログソース一覧 | 200 | 必要 |
| GET | `/api/log-sources/status` | ログソースステータス一覧 | 200 | 必要 |
| POST | `/api/log-sources/` | ログソース作成 | 201 / 422 | 必要（admin） |
| GET | `/api/log-sources/{id}` | ログソース取得 | 200 / 404 | 必要 |
| PUT | `/api/log-sources/{id}` | ログソース更新 | 200 / 404 | 必要（admin） |
| DELETE | `/api/log-sources/{id}` | ログソース削除 | 204 / 404 | 必要（admin） |

#### アラート (`/api/alerts`)

| メソッド | パス | 説明 | ステータスコード | 認証 |
|---------|------|------|----------------|------|
| GET | `/api/alerts/` | アラート一覧 | 200 | 必要 |
| GET | `/api/alerts/count` | 未確認アラート件数 | 200 | 必要 |
| POST | `/api/alerts/` | 手動アラート作成 | 201 | 必要 |
| GET | `/api/alerts/{id}` | アラート取得 | 200 / 404 | 必要 |
| PATCH | `/api/alerts/{id}/acknowledge` | アラート確認 | 200 / 404 | 必要 |
| PATCH | `/api/alerts/{id}/deactivate` | アラート非活性化 | 200 / 404 | 必要 |
| DELETE | `/api/alerts/{id}` | アラート削除 | 204 / 404 | 必要（admin） |

#### アラートルール (`/api/alert-rules`)

| メソッド | パス | 説明 | ステータスコード | 認証 |
|---------|------|------|----------------|------|
| GET | `/api/alert-rules/` | アラートルール一覧 | 200 | 必要 |
| POST | `/api/alert-rules/` | アラートルール作成 | 201 | 必要（admin） |
| GET | `/api/alert-rules/{id}` | アラートルール取得 | 200 / 404 | 必要 |
| PUT | `/api/alert-rules/{id}` | アラートルール更新 | 200 / 404 | 必要（admin） |
| DELETE | `/api/alert-rules/{id}` | アラートルール削除 | 204 / 404 | 必要（admin） |

#### カレンダー — 会議室 (`/api/calendar/rooms`)

| メソッド | パス | 説明 | ステータスコード | 認証 |
|---------|------|------|----------------|------|
| GET | `/api/calendar/rooms` | アクティブ会議室一覧 | 200 | 必要 |
| GET | `/api/calendar/rooms/all` | 全会議室一覧 | 200 | 必要（admin） |
| POST | `/api/calendar/rooms` | 会議室作成 | 201 | 必要（admin） |
| PUT | `/api/calendar/rooms/{id}` | 会議室更新 | 200 / 404 | 必要（admin） |
| DELETE | `/api/calendar/rooms/{id}` | 会議室削除 | 204 / 404 | 必要（admin） |
| GET | `/api/calendar/rooms/{id}/availability` | 会議室空き状況取得 | 200 / 404 | 必要 |

#### カレンダー — イベント (`/api/calendar/events`)

| メソッド | パス | 説明 | ステータスコード | 認証 |
|---------|------|------|----------------|------|
| GET | `/api/calendar/events` | イベント一覧取得（FullCalendar形式） | 200 | 必要 |
| POST | `/api/calendar/events` | イベント作成 | 201 | 必要 |
| GET | `/api/calendar/events/{id}` | イベント詳細取得 | 200 / 404 | 必要 |
| PUT | `/api/calendar/events/{id}` | イベント更新（scope: all/this/series） | 200 / 403 / 404 | 必要 |
| DELETE | `/api/calendar/events/{id}` | イベント削除（scope: all/this/series） | 204 / 403 / 404 | 必要 |

#### カレンダー — 参加者 (`/api/calendar/events/{id}/attendees`)

| メソッド | パス | 説明 | ステータスコード | 認証 |
|---------|------|------|----------------|------|
| POST | `/api/calendar/events/{id}/attendees` | 参加者追加 | 200 | 必要 |
| DELETE | `/api/calendar/events/{id}/attendees/{user_id}` | 参加者削除 | 200 | 必要 |
| PATCH | `/api/calendar/events/{id}/respond` | イベント応答（accept/decline/tentative） | 200 / 404 | 必要 |

#### カレンダー — リマインダー・設定

| メソッド | パス | 説明 | ステータスコード | 認証 |
|---------|------|------|----------------|------|
| PUT | `/api/calendar/events/{id}/reminder` | リマインダー設定 | 200 / 404 | 必要 |
| DELETE | `/api/calendar/events/{id}/reminder` | リマインダー削除 | 200 / 404 | 必要 |
| GET | `/api/calendar/settings` | カレンダー設定取得 | 200 | 必要 |
| PUT | `/api/calendar/settings` | カレンダー設定更新 | 200 | 必要 |

#### 勤怠プリセット (`/api/attendance-presets`)

| メソッド | パス | 説明 | ステータスコード | 認証 |
|---------|------|------|----------------|------|
| GET | `/api/attendance-presets/` | プリセット一覧取得 | 200 | 必要 |

#### OAuthプロバイダ管理 (`/api/admin/oauth-providers`)

| メソッド | パス | 説明 | ステータスコード | 認証 |
|---------|------|------|----------------|------|
| GET | `/api/admin/oauth-providers/` | OAuthプロバイダ一覧 | 200 | 必要（admin） |
| POST | `/api/admin/oauth-providers/` | OAuthプロバイダ作成 | 201 | 必要（admin） |
| PUT | `/api/admin/oauth-providers/{id}` | OAuthプロバイダ更新 | 200 / 404 | 必要（admin） |
| DELETE | `/api/admin/oauth-providers/{id}` | OAuthプロバイダ削除 | 204 / 404 | 必要（admin） |

---

### ページ エンドポイント

| メソッド | パス | 説明 |
|---------|------|------|
| GET | `/login` | ログイン画面 |
| GET | `/forgot-password` | パスワードリセット要求画面 |
| GET | `/reset-password` | パスワード再設定画面 |
| GET | `/` | Dashboard画面 |
| GET | `/todos` | Todo画面 |
| GET | `/todos/public` | 公開Todo一覧画面 |
| GET | `/presence` | 在籍状態一覧画面 |
| GET | `/attendance` | Attendance画面 |
| GET | `/reports` | 日報一覧画面 |
| GET | `/reports/{id}` | 日報詳細画面 |
| GET | `/summary` | 業務サマリー画面 |
| GET | `/tasks` | Tasks画面 |
| GET | `/task-list` | タスクリスト画面 |
| GET | `/logs` | Logs画面 |
| GET | `/alerts` | Alerts画面 |
| GET | `/users` | ユーザー管理画面 |
| GET | `/calendar` | カレンダー画面 |

### WebSocket エンドポイント

| プロトコル | パス | 説明 | 認証 |
|-----------|------|------|------|
| WS | `/ws/logs` | リアルタイムログ配信 | 必要 |
| WS | `/ws/presence` | 在籍状態リアルタイム配信 | 必要 |
| WS | `/ws/alerts` | リアルタイムアラート配信 | 必要 |
