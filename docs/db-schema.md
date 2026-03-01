# データベース設計

> 本ドキュメントは [spec.md](./spec.md) の補足資料です。

---

## 1. ER図（テーブル関係）

```
users (1) ──── (N) todos
users (1) ──── (N) attendances
users (1) ──── (N) tasks
users (1) ──── (N) presence_statuses (UNIQUE)
users (1) ──── (N) presence_logs
users (1) ──── (N) daily_reports
users (1) ──── (N) task_list_items.assignee_id
users (1) ──── (N) task_list_items.created_by
users (1) ──── (N) alerts.acknowledged_by
users (1) ──── (N) calendar_events.creator_id
users (1) ──── (N) calendar_event_attendees.user_id
users (1) ──── (1) user_calendar_settings (UNIQUE)
departments (1) ──── (N) users.department_id (SET NULL)
departments (1) ──── (N) departments.parent_id (SET NULL, 自己参照)
attendance_presets (1) ──── (N) users.default_preset_id
attendances (1) ──── (N) attendance_breaks (CASCADE)
task_categories (1) ──── (N) tasks.category_id
task_categories (1) ──── (N) daily_reports.category_id
task_categories (1) ──── (N) task_list_items.category_id
tasks (1) ──── (N) task_time_entries (CASCADE)
task_list_items (1) ──── (N) tasks.source_item_id (SET NULL)
alert_rules (1) ──── (N) alerts.rule_id (SET NULL)
calendar_events (1) ──── (N) calendar_event_attendees (CASCADE)
calendar_events (1) ──── (N) calendar_event_exceptions (CASCADE)
calendar_events (1) ──── (N) calendar_reminders (CASCADE)
calendar_rooms (1) ──── (N) calendar_events.room_id (SET NULL)
users (1) ──── (N) user_oauth_accounts.user_id (CASCADE)
users (1) ──── (N) auth_audit_logs.user_id (SET NULL)
users (1) ──── (N) password_reset_tokens.user_id (CASCADE)
oauth_providers (1) ──── (N) user_oauth_accounts.provider_id (CASCADE)
log_sources (1) ──── (N) log_source_paths (CASCADE)
log_source_paths (1) ──── (N) log_files.path_id (CASCADE)
log_sources (1) ──── (N) log_files.source_id (CASCADE)
log_files (1) ──── (N) log_entries (CASCADE)
departments (1) ──── (N) log_sources.department_id
site_groups (1) ──── (N) site_links.group_id (SET NULL)
users (1) ──── (N) site_links.created_by (SET NULL)
wiki_categories (1) ──── (N) wiki_pages.category_id (SET NULL)
users (1) ──── (N) wiki_pages.author_id (SET NULL)
users (1) ──── (N) wiki_tags.created_by (SET NULL)
wiki_pages (1) ──── (N) wiki_pages.parent_id (SET NULL, 自己参照)
wiki_pages (N) ──── (N) wiki_tags (wiki_page_tags: CASCADE双方向)
wiki_pages (N) ──── (N) task_list_items (wiki_page_task_items: CASCADE双方向)
wiki_pages (1) ──── (N) wiki_page_tasks (CASCADE)
tasks (1) ──── (N) wiki_page_tasks.task_id (SET NULL)
users (1) ──── (N) wiki_page_task_items.linked_by (SET NULL)
users (1) ──── (N) wiki_page_tasks.linked_by (SET NULL)
wiki_pages (1) ──── (N) wiki_attachments (CASCADE)
roles (1) ──── (N) role_permissions (CASCADE)
roles (N) ──── (N) users (user_roles: CASCADE双方向)
roles (N) ──── (N) menus (role_menus: CASCADE双方向)
departments (N) ──── (N) menus (department_menus: CASCADE双方向)
menus (1) ──── (N) menus.parent_id (SET NULL, 自己参照)
users (N) ──── (N) menus (user_menus: CASCADE双方向)
logs（独立テーブル）
login_attempts（独立テーブル）
oauth_states（独立テーブル）
```

---

## 2. テーブル定義

> **Note**: コアモデル（users, departments, login_attempts, auth_audit_logs, oauth_providers, user_oauth_accounts, oauth_states, password_reset_tokens, roles, role_permissions, user_roles, menus, role_menus, user_menus）の実装は `portal_core/portal_core/models/` に配置されている。`app/models/` には後方互換用の再エクスポートshimが残されており、既存の `from app.models.xxx import` はそのまま動作する。

### 2.1 users テーブル

ユーザー情報を管理する。

| カラム名 | 型 | 制約 | 説明 |
|----------|-----|------|------|
| id | Integer | PK, AUTO_INCREMENT | ユーザーID |
| email | String(255) | NOT NULL, UNIQUE | メールアドレス（ログインID） |
| display_name | String(200) | NOT NULL | 表示名 |
| password_hash | String(255) | NULL許可 | パスワードハッシュ（bcrypt） |
| role | String(20) | NOT NULL, DEFAULT 'user' | ロール（admin/user） |
| is_active | Boolean | DEFAULT true | 有効フラグ |
| default_preset_id | Integer | FK(attendance_presets.id), NULL許可 | デフォルト出勤プリセット |
| department_id | Integer | FK(departments.id, SET NULL), NULL許可, INDEX | 所属部門 |
| locked_until | DateTime(TZ) | NULL許可 | アカウントロック期限 |
| session_version | Integer | NOT NULL, DEFAULT 1 | セッション無効化用バージョン |
| preferred_locale | String(10) | NOT NULL, server_default 'ja' | 優先ロケール (ja/en) |
| created_at | DateTime(TZ) | DEFAULT now() | 作成日時 |
| updated_at | DateTime(TZ) | DEFAULT now(), ON UPDATE now() | 更新日時 |

- モデルファイル: `portal_core/portal_core/models/user.py`（`app/models/user.py` は再エクスポートshim）
- アプリケーション起動時にデフォルトユーザー（id=1, email=`admin@example.com`, role=`admin`）が自動作成される。

### 2.2 todos テーブル

Todoアイテムを管理する。

| カラム名 | 型 | 制約 | 説明 |
|----------|-----|------|------|
| id | Integer | PK, AUTO_INCREMENT | Todo ID |
| user_id | Integer | FK(users.id), NOT NULL | 所有ユーザーID |
| title | String(500) | NOT NULL | タイトル |
| description | Text | NULL許可 | 説明 |
| is_completed | Boolean | DEFAULT false | 完了フラグ |
| priority | Integer | DEFAULT 0 | 優先度 |
| due_date | Date | NULL許可 | 期日 |
| visibility | String(20) | NOT NULL, server_default 'private' | 公開範囲 (private/public) |
| created_at | DateTime(TZ) | DEFAULT now() | 作成日時 |
| updated_at | DateTime(TZ) | DEFAULT now(), ON UPDATE now() | 更新日時 |

- モデルファイル: `app/models/todo.py`

**visibility値:**

| 値 | 説明 |
|----|------|
| `private` | プライベート（本人のみ） |
| `public` | 公開（全員閲覧可） |

**priority値:**

| 値 | 説明 |
|----|------|
| 0 | Normal（通常） |
| 1 | High（高） |
| 2 | Urgent（緊急） |

### 2.3 attendances テーブル

出勤・退勤の記録を管理する。

| カラム名 | 型 | 制約 | 説明 |
|----------|-----|------|------|
| id | Integer | PK, AUTO_INCREMENT | 出勤記録ID |
| user_id | Integer | FK(users.id), NOT NULL | ユーザーID |
| clock_in | DateTime(TZ) | NOT NULL | 出勤日時 |
| clock_out | DateTime(TZ) | NULL許可 | 退勤日時 |
| date | Date | NOT NULL | 出勤日 |
| input_type | String(10) | NOT NULL, server_default 'web' | 入力種別 |
| note | Text | NULL許可 | メモ |
| created_at | DateTime(TZ) | DEFAULT now() | 作成日時 |
| updated_at | DateTime(TZ) | DEFAULT now(), ON UPDATE now() | 更新日時 |

- モデルファイル: `app/models/attendance.py`
- UNIQUE制約: `(user_id, date)` — 同一ユーザー・同一日の重複を防止

**input_type値:**

| 値 | 説明 |
|----|------|
| `web` | Web画面から入力 |
| `ic_card` | ICカード打刻 |
| `admin` | 管理者入力（ロック: 更新・削除・default-set・break-start 不可） |

### 2.4 attendance_breaks テーブル

勤怠の休憩時間を管理する。

| カラム名 | 型 | 制約 | 説明 |
|----------|-----|------|------|
| id | Integer | PK, AUTO_INCREMENT | 休憩ID |
| attendance_id | Integer | FK(attendances.id, CASCADE), NOT NULL | 出勤記録ID |
| break_start | DateTime(TZ) | NOT NULL | 休憩開始日時 |
| break_end | DateTime(TZ) | NULL許可 | 休憩終了日時 |
| created_at | DateTime(TZ) | DEFAULT now() | 作成日時 |

- モデルファイル: `app/models/attendance_break.py`
- 1回の出勤あたり最大3回まで（サービス層で制御）
- 出勤記録削除時に CASCADE で連動削除

### 2.5 attendance_presets テーブル

出勤プリセット（定時パターン）を管理する。

| カラム名 | 型 | 制約 | 説明 |
|----------|-----|------|------|
| id | Integer | PK, AUTO_INCREMENT | プリセットID |
| name | String(100) | NOT NULL | プリセット名 |
| clock_in | String(5) | NOT NULL | 出勤時刻（HH:MM） |
| clock_out | String(5) | NOT NULL | 退勤時刻（HH:MM） |
| break_start | String(5) | NULL許可 | 休憩開始時刻（HH:MM） |
| break_end | String(5) | NULL許可 | 休憩終了時刻（HH:MM） |

- モデルファイル: `app/models/attendance_preset.py`
- アプリ起動時にデフォルト2件をシード（9:00-18:00, 8:30-17:30）

### 2.6 tasks テーブル

時間追跡付きタスクを管理する。

| カラム名 | 型 | 制約 | 説明 |
|----------|-----|------|------|
| id | Integer | PK, AUTO_INCREMENT | タスクID |
| user_id | Integer | FK(users.id), NOT NULL | ユーザーID |
| title | String(500) | NOT NULL | タイトル |
| description | Text | NULL許可 | 説明 |
| status | String(20) | DEFAULT "pending" | ステータス |
| total_seconds | Integer | DEFAULT 0 | 累計作業時間（秒） |
| report | Boolean | DEFAULT false | Done時に日報を自動作成するフラグ |
| category_id | Integer | FK(task_categories.id), NULL許可 | タスク分類ID |
| backlog_ticket_id | String(50) | NULL許可 | Backlogチケット番号（例: WHT-488） |
| source_item_id | Integer | FK(task_list_items.id, SET NULL), NULL許可 | リンク元タスクリストアイテムID |
| created_at | DateTime(TZ) | DEFAULT now() | 作成日時 |
| updated_at | DateTime(TZ) | DEFAULT now(), ON UPDATE now() | 更新日時 |

- モデルファイル: `app/models/task.py`
- Done（完了）操作でタスクは物理削除される（`completed` ステータスにはならない）

**status値:**

| 値 | 説明 |
|----|------|
| `pending` | 未着手（タイマー停止中） |
| `in_progress` | 作業中（タイマー稼働中） |

### 2.7 task_time_entries テーブル

タスクの作業時間エントリを管理する。

| カラム名 | 型 | 制約 | 説明 |
|----------|-----|------|------|
| id | Integer | PK, AUTO_INCREMENT | エントリID |
| task_id | Integer | FK(tasks.id, CASCADE), NOT NULL | タスクID |
| started_at | DateTime(TZ) | NOT NULL | 開始日時 |
| stopped_at | DateTime(TZ) | NULL許可 | 停止日時 |
| elapsed_seconds | Integer | DEFAULT 0 | 経過秒数 |
| created_at | DateTime(TZ) | DEFAULT now() | 作成日時 |

- モデルファイル: `app/models/task_time_entry.py`
- タスク削除時にCASCADEにより関連エントリも削除される。

### 2.8 task_categories テーブル

タスク・日報の分類マスタデータ。

| カラム名 | 型 | 制約 | 説明 |
|----------|-----|------|------|
| id | Integer | PK, AUTO_INCREMENT | カテゴリID |
| name | String(100) | NOT NULL | カテゴリ名 |

- モデルファイル: `app/models/task_category.py`
- アプリ起動時にデフォルトカテゴリをシード（その他, OWVIS(ライト), OPAS 等 16件）
- tasks, daily_reports, task_list_items から FK 参照

### 2.9 logs テーブル

外部システムからのログを管理する。

| カラム名 | 型 | 制約 | 説明 |
|----------|-----|------|------|
| id | Integer | PK, AUTO_INCREMENT | ログID |
| system_name | String(200) | NOT NULL | システム名 |
| log_type | String(100) | NOT NULL | ログ種別 |
| severity | String(20) | DEFAULT "INFO" | 重要度 |
| message | Text | NOT NULL | メッセージ |
| extra_data | JSON | NULL許可 | 追加データ |
| received_at | DateTime(TZ) | DEFAULT now() | 受信日時 |

- モデルファイル: `app/models/log.py`

**severity値:**

| 値 | 説明 |
|----|------|
| `DEBUG` | デバッグ |
| `INFO` | 情報 |
| `WARNING` | 警告 |
| `ERROR` | エラー |
| `CRITICAL` | 致命的 |

### 2.10 presence_statuses テーブル

ユーザーの現在の在籍状態を管理する。

| カラム名 | 型 | 制約 | 説明 |
|----------|-----|------|------|
| id | Integer | PK, AUTO_INCREMENT | ステータスID |
| user_id | Integer | FK(users.id), UNIQUE | ユーザーID |
| status | String(20) | NOT NULL, server_default 'offline' | 在籍ステータス |
| message | Text | NULL許可 | ステータスメッセージ |
| updated_at | DateTime(TZ) | DEFAULT now(), ON UPDATE now() | 更新日時 |

- モデルファイル: `app/models/presence.py`

**status値:**

| 値 | 説明 |
|----|------|
| `available` | 在席 |
| `away` | 離席 |
| `out` | 外出 |
| `break` | 休憩中 |
| `offline` | オフライン |
| `meeting` | 会議中 |
| `remote` | リモート |

### 2.11 presence_logs テーブル

在籍状態の変更履歴を管理する。

| カラム名 | 型 | 制約 | 説明 |
|----------|-----|------|------|
| id | Integer | PK, AUTO_INCREMENT | ログID |
| user_id | Integer | FK(users.id) | ユーザーID |
| status | String(20) | NOT NULL | 変更後のステータス |
| message | Text | NULL許可 | ステータスメッセージ |
| changed_at | DateTime(TZ) | DEFAULT now() | 変更日時 |

- モデルファイル: `app/models/presence.py`

### 2.12 daily_reports テーブル

業務日報を管理する。

| カラム名 | 型 | 制約 | 説明 |
|----------|-----|------|------|
| id | Integer | PK, AUTO_INCREMENT | 日報ID |
| user_id | Integer | FK(users.id), NOT NULL | ユーザーID |
| report_date | Date | NOT NULL | 対象日 |
| category_id | Integer | FK(task_categories.id), NOT NULL | タスク分類ID |
| task_name | String(200) | NOT NULL | タスク名 |
| backlog_ticket_id | String(50) | NULL許可 | Backlogチケット番号（例: WHT-488） |
| time_minutes | Integer | NOT NULL, DEFAULT 0 | 作業時間（分） |
| work_content | Text | NOT NULL | 業務内容 |
| achievements | Text | NULL許可 | 成果・進捗 |
| issues | Text | NULL許可 | 課題・問題 |
| next_plan | Text | NULL許可 | 明日の予定 |
| remarks | Text | NULL許可 | 備考 |
| created_at | DateTime(TZ) | DEFAULT now() | 作成日時 |
| updated_at | DateTime(TZ) | DEFAULT now(), ON UPDATE now() | 更新日時 |

- モデルファイル: `app/models/daily_report.py`
- 同一ユーザー・同一日に複数件作成可能（UNIQUE 制約なし）
- Task Done 時に `report=True` のタスクから自動作成される

### 2.13 log_sources テーブル

ログ収集ソース（リモートサーバー接続情報）を管理する。

| カラム名 | 型 | 制約 | 説明 |
|----------|-----|------|------|
| id | Integer | PK, AUTO_INCREMENT | ソースID |
| name | String(200) | NOT NULL | ソース表示名 |
| department_id | Integer | FK(departments.id), NOT NULL | 部門ID |
| access_method | String(10) | NOT NULL | アクセス方式 (ftp/smb) |
| host | String(255) | NOT NULL | ホスト名/IPアドレス |
| port | Integer | NULL許可 | ポート番号（NULL=デフォルト: FTP=21, SMB=445） |
| username | String(500) | NOT NULL | ユーザー名（暗号化） |
| password | String(500) | NOT NULL | パスワード（暗号化） |
| domain | String(200) | NULL許可 | SMBドメイン（SMB接続時のみ） |
| encoding | String(20) | NOT NULL, server_default 'utf-8' | ファイルエンコーディング |
| source_type | String(20) | NOT NULL, server_default 'OTHER' | ソース種別 |
| polling_interval_sec | Integer | NOT NULL, DEFAULT 60 | ポーリング間隔（秒、60-3600） |
| collection_mode | String(20) | NOT NULL, server_default 'metadata_only' | 収集モード |
| parser_pattern | Text | NULL許可 | 正規表現パターン（full_import時のみ使用） |
| severity_field | String(100) | NULL許可 | severity を抽出するグループ名 |
| default_severity | String(20) | NOT NULL, server_default 'INFO' | severity 未抽出時のデフォルト |
| is_enabled | Boolean | NOT NULL, DEFAULT true | 有効/無効 |
| alert_on_change | Boolean | NOT NULL, server_default 'false' | ファイル変更通知フラグ（true: スキャンで変更検出時にアラート生成+フォルダリンク表示） |
| consecutive_errors | Integer | NOT NULL, DEFAULT 0 | 連続エラー回数（自動無効化用） |
| last_checked_at | DateTime(TZ) | NULL許可 | 最終チェック日時 |
| last_error | Text | NULL許可 | 最終エラー |
| created_at | DateTime(TZ) | DEFAULT now() | 作成日時 |
| updated_at | DateTime(TZ) | DEFAULT now(), ON UPDATE now() | 更新日時 |

- モデルファイル: `app/models/log_source.py`
- 監視パスは `log_source_paths` テーブルで管理（1:N）

**access_method値:**

| 値 | 説明 |
|----|------|
| `ftp` | FTP接続（デフォルトポート: 21） |
| `smb` | SMB接続（デフォルトポート: 445） |

**source_type値:**

| 値 | 説明 |
|----|------|
| `WEB` | Webアプリケーション |
| `HT` | HTTPサーバー |
| `BATCH` | バッチ処理 |
| `OTHER` | その他 |

**collection_mode値:**

| 値 | 説明 |
|----|------|
| `metadata_only` | ファイルメタデータ（サイズ・更新日時）のみ収集 |
| `full_import` | ファイル内容を読み込みlog_entriesに取り込み |

### 2.13b log_source_paths テーブル

ログソースの監視パス（ディレクトリ＋ファイルパターン）を管理する。1つのログソースに対して複数のパスを設定可能。

| カラム名 | 型 | 制約 | 説明 |
|----------|-----|------|------|
| id | Integer | PK, AUTO_INCREMENT | パスID |
| source_id | Integer | FK(log_sources.id, CASCADE), NOT NULL, INDEX | ソースID |
| base_path | String(1000) | NOT NULL | リモートフォルダパス |
| file_pattern | String(200) | NOT NULL, server_default '*.log' | ファイル名パターン（glob形式） |
| is_enabled | Boolean | NOT NULL, DEFAULT true | 有効/無効 |
| created_at | DateTime(TZ) | DEFAULT now() | 作成日時 |
| updated_at | DateTime(TZ) | DEFAULT now(), ON UPDATE now() | 更新日時 |

- モデルファイル: `app/models/log_source_path.py`
- ソース削除時に CASCADE で連動削除

### 2.14 alert_rules テーブル

アラート生成ルールを管理する。

| カラム名 | 型 | 制約 | 説明 |
|----------|-----|------|------|
| id | Integer | PK, AUTO_INCREMENT | ルールID |
| name | String(200) | NOT NULL | ルール名 |
| condition | JSON | NOT NULL | マッチ条件 |
| alert_title_template | String(500) | NOT NULL | タイトルテンプレート |
| alert_message_template | Text | NULL許可 | メッセージテンプレート |
| severity | String(20) | DEFAULT "warning" | 生成アラートの重要度 |
| is_enabled | Boolean | DEFAULT true | ルール有効/無効 |
| created_at | DateTime(TZ) | DEFAULT now() | 作成日時 |
| updated_at | DateTime(TZ) | DEFAULT now(), ON UPDATE now() | 更新日時 |

- モデルファイル: `app/models/alert.py`

**severity値（アラート系）:**

| 値 | 説明 |
|----|------|
| `info` | 情報 |
| `warning` | 警告 |
| `critical` | 致命的 |

> **注意**: `logs` テーブルの severity（大文字5段階: `DEBUG`/`INFO`/`WARNING`/`ERROR`/`CRITICAL`）と `alerts`/`alert_rules` テーブルの severity（小文字3段階: `info`/`warning`/`critical`）は体系が異なる。アラートルールの `condition` でログの severity をマッチングする際は、ログ側の大文字値（例: `"ERROR"`）を指定する必要がある。

### 2.15 alerts テーブル

システムアラートを管理する。

| カラム名 | 型 | 制約 | 説明 |
|----------|-----|------|------|
| id | Integer | PK, AUTO_INCREMENT | アラートID |
| title | String(500) | NOT NULL | アラートタイトル |
| message | Text | NOT NULL | アラートメッセージ |
| severity | String(20) | DEFAULT "info" | 重要度 (critical/warning/info) |
| source | String(200) | NULL許可 | アラートソース |
| rule_id | Integer | FK(alert_rules.id, SET NULL), NULL許可 | 自動生成元ルール |
| is_active | Boolean | DEFAULT true | アクティブフラグ |
| acknowledged | Boolean | DEFAULT false | 確認済みフラグ |
| acknowledged_by | Integer | FK(users.id, SET NULL), NULL許可 | 確認者のuser_id |
| acknowledged_at | DateTime(TZ) | NULL許可 | 確認日時 |
| created_at | DateTime(TZ) | DEFAULT now() | 発生日時 |

- モデルファイル: `app/models/alert.py`

### 2.16 task_list_items テーブル

タスクリストアイテム（バックログ）を管理する。

| カラム名 | 型 | 制約 | 説明 |
|----------|-----|------|------|
| id | Integer | PK, AUTO_INCREMENT | アイテムID |
| title | String(500) | NOT NULL | タイトル |
| description | Text | NULL許可 | 説明 |
| scheduled_date | Date | NULL許可 | 予定日 |
| assignee_id | Integer | FK(users.id), NULL許可 | 担当者ID（NULL=未割当） |
| created_by | Integer | FK(users.id), NOT NULL | 作成者ID |
| status | String(20) | NOT NULL, DEFAULT "open" | ステータス (open/in_progress/done) |
| total_seconds | Integer | NOT NULL, DEFAULT 0 | 累計作業時間（秒、Task完了時に蓄積） |
| category_id | Integer | FK(task_categories.id), NULL許可 | タスク分類ID |
| backlog_ticket_id | String(50) | NULL許可 | Backlogチケット番号 |
| created_at | DateTime(TZ) | DEFAULT now() | 作成日時 |
| updated_at | DateTime(TZ) | DEFAULT now(), ON UPDATE now() | 更新日時 |

- モデルファイル: `app/models/task_list_item.py`
- `assignee_id` が NULL のアイテムは「未割当」として全ユーザーに公開される。

**status値:**

| 値 | 説明 |
|----|------|
| `open` | 未着手 |
| `in_progress` | 作業中（Taskにコピー済み） |
| `done` | 完了 |

### 2.17 departments テーブル

部門・組織ツリーを管理する。`parent_id` による自己参照で階層構造（ツリー）を表現する。

| カラム名 | 型 | 制約 | 説明 |
|----------|-----|------|------|
| id | Integer | PK, AUTO_INCREMENT | 部門ID |
| name | String(100) | NOT NULL, UNIQUE | 部門名 |
| code | String(50) | NULL許可, UNIQUE | 部門コード（例: DEV, SALES） |
| description | String(500) | NULL許可 | 説明 |
| parent_id | Integer | FK(departments.id, SET NULL), NULL許可, INDEX | 親部門ID（自己参照、NULL=ルート部門） |
| sort_order | Integer | NOT NULL, DEFAULT 0 | 兄弟部門間の表示順 |
| is_active | Boolean | NOT NULL, DEFAULT true | 有効フラグ（無効部門はツリー表示から除外） |
| created_at | DateTime(TZ) | DEFAULT now() | 作成日時 |
| updated_at | DateTime(TZ) | DEFAULT now(), ON UPDATE now() | 更新日時 |

- モデルファイル: `portal_core/portal_core/models/department.py`（`app/models/` には再エクスポートshim）
- UNIQUE インデックス: `name`, `code`
- 旧 `groups` テーブル（フラット構造）から移行（マイグレーション `b7c8d9e0f1a2`）

### 2.18 calendar_events テーブル

カレンダーイベントを管理する。

| カラム名 | 型 | 制約 | 説明 |
|----------|-----|------|------|
| id | Integer | PK, AUTO_INCREMENT | イベントID |
| title | String(500) | NOT NULL | タイトル |
| description | Text | NULL許可 | 説明 |
| event_type | String(20) | NOT NULL, DEFAULT "event" | イベント種別 |
| start_at | DateTime(TZ) | NOT NULL | 開始日時 |
| end_at | DateTime(TZ) | NULL許可 | 終了日時 |
| all_day | Boolean | NOT NULL, DEFAULT false | 終日フラグ |
| room_id | Integer | FK(calendar_rooms.id, SET NULL), NULL許可, INDEX | 会議室ID |
| location | String(200) | NULL許可 | 場所 |
| color | String(7) | NULL許可 | 表示色 |
| visibility | String(10) | NOT NULL, DEFAULT "public" | 公開範囲 |
| recurrence_rule | String(500) | NULL許可 | 繰り返しルール |
| recurrence_end | Date | NULL許可 | 繰り返し終了日 |
| source_type | String(20) | NULL許可 | 連携元種別 |
| source_id | Integer | NULL許可 | 連携元ID |
| creator_id | Integer | FK(users.id), NOT NULL, INDEX | 作成者ID |
| created_at | DateTime(TZ) | DEFAULT now() | 作成日時 |
| updated_at | DateTime(TZ) | DEFAULT now(), ON UPDATE now() | 更新日時 |

- モデルファイル: `app/models/calendar_event.py`

**event_type値:**

| 値 | 説明 |
|----|------|
| `event` | 通常イベント |
| `meeting` | 会議 |
| `task` | タスク連携 |

### 2.19 calendar_event_exceptions テーブル

繰り返しイベントの例外（削除・変更）を管理する。

| カラム名 | 型 | 制約 | 説明 |
|----------|-----|------|------|
| id | Integer | PK, AUTO_INCREMENT | 例外ID |
| parent_event_id | Integer | FK(calendar_events.id, CASCADE), NOT NULL | 親イベントID |
| original_date | Date | NOT NULL | 元の日付 |
| is_deleted | Boolean | NOT NULL, DEFAULT false | 削除フラグ |
| override_event_id | Integer | FK(calendar_events.id, SET NULL), NULL許可 | 変更後イベントID |

- モデルファイル: `app/models/calendar_event.py`

### 2.20 calendar_rooms テーブル

会議室を管理する。

| カラム名 | 型 | 制約 | 説明 |
|----------|-----|------|------|
| id | Integer | PK, AUTO_INCREMENT | 会議室ID |
| name | String(100) | NOT NULL, UNIQUE | 会議室名 |
| description | String(500) | NULL許可 | 説明 |
| capacity | Integer | NULL許可 | 定員 |
| color | String(7) | NULL許可 | 表示色 |
| sort_order | Integer | NOT NULL, DEFAULT 0 | 表示順 |
| is_active | Boolean | NOT NULL, DEFAULT true | 有効フラグ |
| created_at | DateTime(TZ) | DEFAULT now() | 作成日時 |

- モデルファイル: `app/models/calendar_room.py`

### 2.21 calendar_event_attendees テーブル

イベント参加者を管理する。

| カラム名 | 型 | 制約 | 説明 |
|----------|-----|------|------|
| id | Integer | PK, AUTO_INCREMENT | 参加者ID |
| event_id | Integer | FK(calendar_events.id, CASCADE), NOT NULL, INDEX | イベントID |
| user_id | Integer | FK(users.id), NOT NULL, INDEX | ユーザーID |
| response_status | String(10) | NOT NULL, DEFAULT "pending" | 応答状態 |
| created_at | DateTime(TZ) | DEFAULT now() | 作成日時 |

- モデルファイル: `app/models/calendar_event_attendee.py`
- UNIQUE制約: `(event_id, user_id)`

**response_status値:**

| 値 | 説明 |
|----|------|
| `pending` | 未回答 |
| `accepted` | 参加 |
| `declined` | 不参加 |
| `tentative` | 未定 |

### 2.22 calendar_reminders テーブル

イベントリマインダーを管理する。

| カラム名 | 型 | 制約 | 説明 |
|----------|-----|------|------|
| id | Integer | PK, AUTO_INCREMENT | リマインダーID |
| event_id | Integer | FK(calendar_events.id, CASCADE), NOT NULL | イベントID |
| user_id | Integer | FK(users.id), NOT NULL | ユーザーID |
| minutes_before | Integer | NOT NULL, DEFAULT 10 | 何分前に通知 |
| remind_at | DateTime(TZ) | NOT NULL | 通知予定日時 |
| is_sent | Boolean | NOT NULL, DEFAULT false | 送信済みフラグ |
| created_at | DateTime(TZ) | DEFAULT now() | 作成日時 |

- モデルファイル: `app/models/calendar_reminder.py`
- 複合インデックス: `(remind_at, is_sent)`

### 2.23 user_calendar_settings テーブル

ユーザーごとのカレンダー設定を管理する。

| カラム名 | 型 | 制約 | 説明 |
|----------|-----|------|------|
| id | Integer | PK, AUTO_INCREMENT | 設定ID |
| user_id | Integer | FK(users.id), NOT NULL, UNIQUE | ユーザーID |
| default_color | String(7) | NOT NULL, DEFAULT "#3788d8" | デフォルト表示色 |
| default_view | String(20) | NOT NULL, DEFAULT "dayGridMonth" | デフォルト表示 |
| default_reminder_minutes | Integer | NOT NULL, DEFAULT 10 | デフォルトリマインダー（分） |
| show_task_list | Boolean | NOT NULL, DEFAULT true | タスクリスト表示 |
| show_attendance | Boolean | NOT NULL, DEFAULT true | 勤怠表示 |
| show_reports | Boolean | NOT NULL, DEFAULT false | 日報表示 |
| working_hours_start | String(5) | NOT NULL, DEFAULT "09:00" | 勤務開始時刻 |
| working_hours_end | String(5) | NOT NULL, DEFAULT "18:00" | 勤務終了時刻 |

- モデルファイル: `app/models/user_calendar_setting.py`

### 2.24 login_attempts テーブル

ログイン試行を記録する。

| カラム名 | 型 | 制約 | 説明 |
|----------|-----|------|------|
| id | Integer | PK, AUTO_INCREMENT | ID |
| email | String(255) | NOT NULL, INDEX | 試行メールアドレス |
| ip_address | String(45) | NULL許可 | クライアントIPアドレス |
| success | Boolean | NOT NULL | 成否 |
| attempted_at | DateTime(TZ) | DEFAULT now(), INDEX | 試行日時 |

- モデルファイル: `portal_core/portal_core/models/login_attempt.py`（`app/models/login_attempt.py` は再エクスポートshim）

### 2.25 auth_audit_logs テーブル

認証関連の監査ログを管理する。

| カラム名 | 型 | 制約 | 説明 |
|----------|-----|------|------|
| id | Integer | PK, AUTO_INCREMENT | ID |
| user_id | Integer | FK(users.id, SET NULL), NULL許可 | ユーザーID |
| event_type | String(50) | NOT NULL, INDEX | イベント種別 |
| email | String(255) | NULL許可 | 使用メールアドレス |
| ip_address | String(45) | NULL許可 | クライアントIPアドレス |
| user_agent | String(500) | NULL許可 | ブラウザUA |
| details | JSON | NULL許可 | 追加情報 |
| created_at | DateTime(TZ) | DEFAULT now() | 日時 |

- モデルファイル: `portal_core/portal_core/models/auth_audit_log.py`（`app/models/auth_audit_log.py` は再エクスポートshim）

**event_type値:**

| 値 | 説明 |
|----|------|
| `login_success` | ログイン成功 |
| `login_failure` | ログイン失敗 |
| `logout` | ログアウト |
| `password_change` | パスワード変更 |
| `password_reset` | パスワードリセット（管理者） |
| `account_locked` | アカウントロック |
| `account_unlocked` | アカウントアンロック |
| `role_changed` | ロール変更 |
| `session_invalidated` | セッション無効化 |
| `oauth_login` | OAuthログイン |
| `oauth_link` | OAuthアカウントリンク |

### 2.26 oauth_providers テーブル

OAuthプロバイダ設定を管理する。

| カラム名 | 型 | 制約 | 説明 |
|----------|-----|------|------|
| id | Integer | PK, AUTO_INCREMENT | プロバイダID |
| name | String(50) | NOT NULL, UNIQUE | プロバイダ名 (google/github等) |
| display_name | String(100) | NOT NULL | 表示名 |
| client_id | String(255) | NOT NULL | OAuth Client ID |
| client_secret | String(255) | NOT NULL | OAuth Client Secret |
| authorize_url | String(500) | NOT NULL | 認証エンドポイント |
| token_url | String(500) | NOT NULL | トークンエンドポイント |
| userinfo_url | String(500) | NOT NULL | ユーザー情報エンドポイント |
| scopes | String(500) | NOT NULL | スコープ（スペース区切り） |
| is_enabled | Boolean | DEFAULT true | 有効/無効 |
| created_at | DateTime(TZ) | DEFAULT now() | 作成日時 |
| updated_at | DateTime(TZ) | DEFAULT now(), ON UPDATE now() | 更新日時 |

- モデルファイル: `portal_core/portal_core/models/oauth_provider.py`（`app/models/oauth_provider.py` は再エクスポートshim）

### 2.27 user_oauth_accounts テーブル

ユーザーとOAuthプロバイダのリンクを管理する。

| カラム名 | 型 | 制約 | 説明 |
|----------|-----|------|------|
| id | Integer | PK, AUTO_INCREMENT | ID |
| user_id | Integer | FK(users.id, CASCADE), NOT NULL | ローカルユーザーID |
| provider_id | Integer | FK(oauth_providers.id, CASCADE), NOT NULL | プロバイダID |
| provider_user_id | String(255) | NOT NULL | プロバイダ側ユーザーID |
| provider_email | String(255) | NULL許可 | プロバイダ側メールアドレス |
| access_token | String(2000) | NULL許可 | アクセストークン |
| refresh_token | String(2000) | NULL許可 | リフレッシュトークン |
| token_expires_at | DateTime(TZ) | NULL許可 | トークン有効期限 |
| created_at | DateTime(TZ) | DEFAULT now() | 作成日時 |
| updated_at | DateTime(TZ) | DEFAULT now(), ON UPDATE now() | 更新日時 |

- モデルファイル: `portal_core/portal_core/models/user_oauth_account.py`（`app/models/user_oauth_account.py` は再エクスポートshim）
- UNIQUE制約: `(provider_id, provider_user_id)`

### 2.28 oauth_states テーブル

OAuthフローのCSRF防止用stateを管理する。

| カラム名 | 型 | 制約 | 説明 |
|----------|-----|------|------|
| id | Integer | PK, AUTO_INCREMENT | ID |
| state | String(128) | NOT NULL, UNIQUE | ランダムstate値 |
| code_verifier | String(128) | NULL許可 | PKCE code_verifier |
| redirect_uri | String(500) | NULL許可 | リダイレクト先URL |
| created_at | DateTime(TZ) | DEFAULT now() | 作成日時 |
| expires_at | DateTime(TZ) | NOT NULL | 有効期限（デフォルト5分） |

- モデルファイル: `portal_core/portal_core/models/oauth_state.py`（`app/models/oauth_state.py` は再エクスポートshim）

### 2.29 password_reset_tokens テーブル

パスワードリセットトークンを管理する。

| カラム名 | 型 | 制約 | 説明 |
|----------|-----|------|------|
| id | Integer | PK, AUTO_INCREMENT | ID |
| user_id | Integer | FK(users.id, CASCADE), INDEX | ユーザーID |
| token_hash | String(255) | NOT NULL, UNIQUE | SHA-256ハッシュ（平文は保存しない） |
| is_used | Boolean | NOT NULL, DEFAULT false | 使用済みフラグ |
| created_at | DateTime(TZ) | DEFAULT now() | 作成日時 |
| expires_at | DateTime(TZ) | NOT NULL | 有効期限 |

- モデルファイル: `portal_core/portal_core/models/password_reset_token.py`（`app/models/password_reset_token.py` は再エクスポートshim）
- トークンは SHA-256 ハッシュのみ DB に保存（DB漏洩対策）
- 物理削除ではなくフラグ管理（監査証跡のため）

### 2.30 log_files テーブル

ログソースから検出されたファイルを管理する。

| カラム名 | 型 | 制約 | 説明 |
|----------|-----|------|------|
| id | Integer | PK, AUTO_INCREMENT | ファイルID |
| source_id | Integer | FK(log_sources.id, CASCADE), NOT NULL, INDEX | ソースID |
| path_id | Integer | FK(log_source_paths.id, CASCADE), NOT NULL, INDEX | パスID |
| file_name | String(500) | NOT NULL | ファイル名 |
| file_size | BigInteger | NOT NULL, DEFAULT 0 | ファイルサイズ（バイト） |
| file_modified_at | DateTime(TZ) | NULL許可 | ファイル更新日時 |
| last_read_line | Integer | NOT NULL, DEFAULT 0 | 最終読込行番号（full_importの差分取込用） |
| status | String(20) | NOT NULL, server_default 'new' | ファイルステータス |
| created_at | DateTime(TZ) | DEFAULT now() | 作成日時 |
| updated_at | DateTime(TZ) | DEFAULT now(), ON UPDATE now() | 更新日時 |

- モデルファイル: `app/models/log_file.py`
- UNIQUE制約: `(path_id, file_name)`
- `source_id` はクエリ利便性のために維持（集計・検索用）
- ソース/パス削除時に CASCADE で連動削除

**status値:**

| 値 | 説明 |
|----|------|
| `new` | 新規検出 |
| `unchanged` | 前回から変更なし |
| `updated` | 前回から更新あり |
| `deleted` | リモートから削除済み |
| `error` | エラー |

### 2.31 log_entries テーブル

ログファイルから取り込んだエントリ（行）を管理する。

| カラム名 | 型 | 制約 | 説明 |
|----------|-----|------|------|
| id | Integer | PK, AUTO_INCREMENT | エントリID |
| file_id | Integer | FK(log_files.id, CASCADE), NOT NULL, INDEX | ファイルID |
| line_number | Integer | NOT NULL | 行番号 |
| severity | String(20) | NOT NULL, server_default 'INFO' | 重要度 |
| message | Text | NOT NULL | メッセージ |
| received_at | DateTime(TZ) | DEFAULT now() | 取込日時 |

- モデルファイル: `app/models/log_entry.py`
- 複合インデックス: `(file_id, line_number)`
- インデックス: `received_at`
- ファイル削除時に CASCADE で連動削除

### 2.32 site_groups テーブル

サイトリンクのグループ（カテゴリ）を管理する。

| カラム名 | 型 | 制約 | 説明 |
|----------|-----|------|------|
| id | Integer | PK, AUTO_INCREMENT | グループID |
| name | String(100) | NOT NULL, UNIQUE | グループ名 |
| description | String(500) | NULL許可 | 説明 |
| color | String(7) | NOT NULL, server_default '#6c757d' | 表示色（HEX） |
| icon | String(50) | NULL許可 | アイコンクラス名 |
| sort_order | Integer | NOT NULL, DEFAULT 0 | 表示順 |
| created_at | DateTime(TZ) | DEFAULT now() | 作成日時 |

- モデルファイル: `app/models/site_link.py`

### 2.33 site_links テーブル

サイトリンク（URLブックマーク + ヘルスチェック）を管理する。

| カラム名 | 型 | 制約 | 説明 |
|----------|-----|------|------|
| id | Integer | PK, AUTO_INCREMENT | リンクID |
| name | String(200) | NOT NULL | サイト名 |
| url | String(2000) | NOT NULL | URL |
| description | String(500) | NULL許可 | 説明 |
| group_id | Integer | FK(site_groups.id, SET NULL), NULL許可, INDEX | グループID |
| created_by | Integer | FK(users.id, SET NULL), NULL許可, INDEX | 作成者ID |
| sort_order | Integer | NOT NULL, DEFAULT 0 | 表示順 |
| is_enabled | Boolean | NOT NULL, DEFAULT true | 有効フラグ |
| check_enabled | Boolean | NOT NULL, DEFAULT true | ヘルスチェック有効フラグ |
| check_interval_sec | Integer | NOT NULL, DEFAULT 300 | チェック間隔（秒、60-3600） |
| check_timeout_sec | Integer | NOT NULL, DEFAULT 10 | チェックタイムアウト（秒、3-60） |
| check_ssl_verify | Boolean | NOT NULL, DEFAULT true | SSL証明書検証 |
| status | String(20) | NOT NULL, server_default 'unknown' | ステータス |
| response_time_ms | Integer | NULL許可 | レスポンスタイム（ms） |
| http_status_code | Integer | NULL許可 | HTTPステータスコード |
| last_checked_at | DateTime(TZ) | NULL許可 | 最終チェック日時 |
| last_status_changed_at | DateTime(TZ) | NULL許可 | 最終ステータス変更日時 |
| consecutive_failures | Integer | NOT NULL, DEFAULT 0 | 連続失敗回数 |
| last_error | Text | NULL許可 | 最終エラー |
| created_at | DateTime(TZ) | DEFAULT now() | 作成日時 |
| updated_at | DateTime(TZ) | DEFAULT now(), ON UPDATE now() | 更新日時 |

- モデルファイル: `app/models/site_link.py`

**status値:**

| 値 | 説明 |
|----|------|
| `unknown` | 未チェック |
| `up` | 正常稼働 |
| `down` | 停止 |
| `error` | エラー |

### 2.34 wiki_categories テーブル

Wikiページのカテゴリマスタを管理する。

| カラム名 | 型 | 制約 | 説明 |
|----------|-----|------|------|
| id | Integer | PK, AUTO_INCREMENT | カテゴリID |
| name | String(100) | NOT NULL, UNIQUE | カテゴリ名 |
| description | String(500) | NULL許可 | 説明 |
| color | String(7) | NOT NULL, DEFAULT '#6c757d' | 表示色（HEX） |
| sort_order | Integer | NOT NULL, DEFAULT 0 | 表示順 |
| created_at | DateTime(TZ) | DEFAULT now() | 作成日時 |

- モデルファイル: `app/models/wiki_category.py`
- UNIQUE インデックス: `idx_wiki_categories_name`

### 2.35 wiki_tags テーブル

Wikiページのタグマスタを管理する。

| カラム名 | 型 | 制約 | 説明 |
|----------|-----|------|------|
| id | Integer | PK, AUTO_INCREMENT | タグID |
| name | String(100) | NOT NULL, UNIQUE | タグ名 |
| slug | String(100) | NOT NULL, UNIQUE, INDEX | URLスラッグ（自動生成） |
| color | String(7) | NOT NULL, DEFAULT '#6c757d' | 表示色（HEX） |
| created_by | Integer | FK(users.id, SET NULL), NULL許可 | 作成者ID |
| created_at | DateTime(TZ) | DEFAULT now() | 作成日時 |

- モデルファイル: `app/models/wiki_tag.py`
- UNIQUE インデックス: `idx_wiki_tags_name`, `idx_wiki_tags_slug`

### 2.36 wiki_pages テーブル

Wikiページ本文（階層構造付き）を管理する。

| カラム名 | 型 | 制約 | 説明 |
|----------|-----|------|------|
| id | Integer | PK, AUTO_INCREMENT | ページID |
| title | String(500) | NOT NULL | ページタイトル |
| slug | String(500) | NOT NULL, UNIQUE, INDEX | URLスラッグ（自動生成、重複時は数字サフィックス付与） |
| parent_id | Integer | FK(wiki_pages.id, SET NULL), NULL許可, INDEX | 親ページID（自己参照） |
| content | Text | DEFAULT "" | ページ本文（Markdown形式） |
| author_id | Integer | FK(users.id, SET NULL), NULL許可, INDEX | 作成者ID |
| sort_order | Integer | NOT NULL, DEFAULT 0 | 兄弟ページ間の表示順 |
| visibility | String(20) | NOT NULL, server_default 'local' | 公開範囲 |
| category_id | Integer | FK(wiki_categories.id, SET NULL), NULL許可, INDEX | カテゴリID |
| search_vector | TSVECTOR | NULL許可 | PostgreSQL全文検索ベクタ（自動更新） |
| created_at | DateTime(TZ) | DEFAULT now() | 作成日時 |
| updated_at | DateTime(TZ) | DEFAULT now(), ON UPDATE now() | 更新日時 |

- モデルファイル: `app/models/wiki_page.py`
- GIN インデックス: `idx_wiki_pages_search`（search_vector全文検索用）
- DB トリガー: `wiki_pages_search_update`（title INSERT/UPDATE 時に search_vector を自動更新）
- 循環参照防止: サービス層で `parent_id` の循環を検出して 400 Bad Request を返す

**visibility値:**

| 値 | 説明 |
|----|------|
| `local` | 自部署（同一グループのユーザーのみ）— デフォルト |
| `public` | 他部署（全ログインユーザー） |
| `private` | 非公開（作成者のみ） |

### 2.37 wiki_page_tags テーブル（中間テーブル）

Wikiページとタグの多対多関係を管理する。

| カラム名 | 型 | 制約 | 説明 |
|----------|-----|------|------|
| page_id | Integer | PK, FK(wiki_pages.id, CASCADE) | ページID |
| tag_id | Integer | PK, FK(wiki_tags.id, CASCADE) | タグID |

- モデルファイル: `app/models/wiki_page.py`（Association Table）
- 複合主キー: `(page_id, tag_id)`
- インデックス: `idx_wiki_page_tags_tag_id`
- ページ/タグ削除時に CASCADE で連動削除

### 2.38 wiki_page_task_items テーブル（中間テーブル）

Wikiページとタスクリストアイテムの多対多関係を管理する（永続リンク）。

| カラム名 | 型 | 制約 | 説明 |
|----------|-----|------|------|
| page_id | Integer | PK, FK(wiki_pages.id, CASCADE) | ページID |
| task_item_id | Integer | PK, FK(task_list_items.id, CASCADE) | タスクリストアイテムID |
| linked_by | Integer | FK(users.id, SET NULL), NULL許可 | リンク作成者ID |
| linked_at | DateTime(TZ) | DEFAULT now() | リンク作成日時 |

- モデルファイル: `app/models/wiki_page_task_item.py`
- 複合主キー: `(page_id, task_item_id)`
- ページ/タスクリストアイテム削除時に CASCADE で連動削除

### 2.39 wiki_page_tasks テーブル

Wikiページと進行中タスクのリンクを管理する（タイトルスナップショット付き）。

| カラム名 | 型 | 制約 | 説明 |
|----------|-----|------|------|
| id | Integer | PK, AUTO_INCREMENT | リンクID |
| page_id | Integer | FK(wiki_pages.id, CASCADE), NOT NULL, INDEX | ページID |
| task_id | Integer | FK(tasks.id, SET NULL), NULL許可, INDEX | タスクID（タスク削除後は NULL） |
| task_title | String(500) | NOT NULL | タスクタイトルのスナップショット |
| linked_by | Integer | FK(users.id, SET NULL), NULL許可 | リンク作成者ID |
| linked_at | DateTime(TZ) | DEFAULT now() | リンク作成日時 |

- モデルファイル: `app/models/wiki_page_task.py`
- 部分 UNIQUE インデックス: `(page_id, task_id) WHERE task_id IS NOT NULL`
- ページ削除時に CASCADE で連動削除
- タスク削除時は `task_id` が SET NULL（スナップショットタイトルは保持）

### 2.40 wiki_attachments テーブル

Wikiページに添付されたファイルのメタデータを管理する。物理ファイルは `uploads/wiki/{page_id}/{stored_filename}` に保存される。

| カラム名 | 型 | 制約 | 説明 |
|----------|-----|------|------|
| id | Integer | PK, AUTO_INCREMENT | 添付ファイルID |
| page_id | Integer | FK(wiki_pages.id, CASCADE), NOT NULL, INDEX | ページID |
| filename | String(500) | NOT NULL | 表示用ファイル名（元のファイル名） |
| stored_path | String(1000) | NOT NULL | ディスク上の相対パス |
| mime_type | String(200) | NULL許可 | MIMEタイプ |
| file_size | Integer | NOT NULL, server_default 0 | ファイルサイズ（バイト） |
| created_at | DateTime(TZ) | DEFAULT now() | 作成日時 |

- モデルファイル: `app/models/wiki_attachment.py`
- インデックス: `idx_wiki_attachments_page_id`
- ページ削除時に CASCADE で連動削除
- `after_delete` SQLAlchemy イベントリスナーで物理ファイルも自動削除

### 2.41 roles テーブル

ロール（権限グループ）を管理する。

| カラム名 | 型 | 制約 | 説明 |
|----------|-----|------|------|
| id | Integer | PK, AUTO_INCREMENT | ロールID |
| name | String(100) | NOT NULL, UNIQUE | ロール名（一意） |
| display_name | String(200) | NOT NULL | 表示名 |
| description | String(500) | NULL許可 | 説明 |
| sort_order | Integer | NOT NULL, DEFAULT 0 | 表示順 |
| is_active | Boolean | NOT NULL, DEFAULT true | 有効フラグ |
| created_at | DateTime(TZ) | DEFAULT now() | 作成日時 |
| updated_at | DateTime(TZ) | DEFAULT now(), ON UPDATE now() | 更新日時 |

- モデルファイル: `portal_core/portal_core/models/role.py`
- ロール削除時に関連する `role_permissions` が CASCADE で連動削除

### 2.42 role_permissions テーブル

ロールに付与されたリソース+アクション単位の権限を管理する。

| カラム名 | 型 | 制約 | 説明 |
|----------|-----|------|------|
| id | Integer | PK, AUTO_INCREMENT | 権限ID |
| role_id | Integer | FK(roles.id, CASCADE), NOT NULL, INDEX | ロールID |
| resource | String(100) | NOT NULL | リソース名（例: "wiki", "admin", "*"） |
| action | String(100) | NOT NULL | アクション名（例: "edit", "view", "*"） |
| kino_kbn | SmallInteger | NOT NULL, DEFAULT 1 | 許可/拒否（1=許可, 0=拒否） |

- モデルファイル: `portal_core/portal_core/models/role.py`
- UNIQUE制約: `(role_id, resource, action)`
- ロール削除時に CASCADE で連動削除

### 2.43 user_roles テーブル

ユーザーとロールの多対多関係を管理する。

| カラム名 | 型 | 制約 | 説明 |
|----------|-----|------|------|
| id | Integer | PK, AUTO_INCREMENT | ID |
| user_id | Integer | FK(users.id, CASCADE), NOT NULL, INDEX | ユーザーID |
| role_id | Integer | FK(roles.id, CASCADE), NOT NULL, INDEX | ロールID |
| created_at | DateTime(TZ) | DEFAULT now() | 作成日時 |

- モデルファイル: `portal_core/portal_core/models/role.py`
- UNIQUE制約: `(user_id, role_id)`
- ユーザーまたはロール削除時に CASCADE で連動削除

### 2.44 menus テーブル

ナビゲーションメニュー項目を管理する（階層構造付き）。

| カラム名 | 型 | 制約 | 説明 |
|----------|-----|------|------|
| id | Integer | PK, AUTO_INCREMENT | メニューID |
| name | String(100) | NOT NULL, UNIQUE | メニュー名（一意） |
| label | String(200) | NOT NULL | 表示ラベル |
| path | String(500) | NOT NULL | URLパス |
| icon | String(100) | NOT NULL, server_default '' | アイコンクラス名 |
| badge_id | String(100) | NULL許可 | バッジHTML要素ID |
| parent_id | Integer | FK(menus.id, SET NULL), NULL許可, INDEX | 親メニューID（自己参照） |
| sort_order | Integer | NOT NULL, DEFAULT 100 | 表示順 |
| is_active | Boolean | NOT NULL, DEFAULT true | 有効フラグ |
| required_resource | String(100) | NULL許可 | 表示に必要なリソース権限（NULL=全認証ユーザーに表示） |
| required_action | String(100) | NULL許可 | 表示に必要なアクション権限 |
| created_at | DateTime(TZ) | DEFAULT now() | 作成日時 |
| updated_at | DateTime(TZ) | DEFAULT now(), ON UPDATE now() | 更新日時 |

- モデルファイル: `portal_core/portal_core/models/menu.py`
- `required_resource` と `required_action` が両方 NULL の場合、全認証ユーザーにメニューが表示される

### 2.45 role_menus テーブル（中間テーブル）

ロール単位のメニュー表示制御を管理する。

| カラム名 | 型 | 制約 | 説明 |
|----------|-----|------|------|
| role_id | Integer | PK, FK(roles.id, CASCADE) | ロールID |
| menu_id | Integer | PK, FK(menus.id, CASCADE) | メニューID |
| kino_kbn | SmallInteger | NOT NULL, DEFAULT 1 | 表示制御（1=表示, 0=非表示） |

- モデルファイル: `portal_core/portal_core/models/menu.py`
- 複合主キー: `(role_id, menu_id)`
- ロールまたはメニュー削除時に CASCADE で連動削除

### 2.46 user_menus テーブル（中間テーブル）

ユーザー単位のメニュー表示制御を管理する（最高優先度）。

| カラム名 | 型 | 制約 | 説明 |
|----------|-----|------|------|
| user_id | Integer | PK, FK(users.id, CASCADE) | ユーザーID |
| menu_id | Integer | PK, FK(menus.id, CASCADE) | メニューID |
| kino_kbn | SmallInteger | NOT NULL, DEFAULT 1 | 表示制御（1=表示, 0=非表示） |

- モデルファイル: `portal_core/portal_core/models/menu.py`
- 複合主キー: `(user_id, menu_id)`
- ユーザーまたはメニュー削除時に CASCADE で連動削除
- `user_menus` の設定が `role_menus` より高優先度で適用される

### 2.47 department_menus テーブル（中間テーブル）

部署単位のメニュー表示制御を管理する。

| カラム名 | 型 | 制約 | 説明 |
|----------|-----|------|------|
| department_id | Integer | PK, FK(departments.id, CASCADE) | 部署ID |
| menu_id | Integer | PK, FK(menus.id, CASCADE) | メニューID |
| kino_kbn | SmallInteger | NOT NULL, DEFAULT 1 | 表示制御（1=表示, 0=非表示） |

- モデルファイル: `portal_core/portal_core/models/menu.py`
- 複合主キー: `(department_id, menu_id)`
- 部署またはメニュー削除時に CASCADE で連動削除
- `user_menus` より低優先度、`role_menus` より高優先度

---

## 3. 初期化処理

デフォルトデータの投入は `portal_core/portal_core/init_db.py`（共通）と `app/init_db.py`（アプリ固有）で管理されている。

### 3.1 seed_default_user()（portal_core）

- デフォルトユーザー（id=1, email=`admin@example.com`, role=`admin`）が存在しない場合に自動作成。
- 既存ユーザーの `password_hash` が未設定の場合、`DEFAULT_PASSWORD` のハッシュを設定。
- `role` が `admin` でない場合、自動修正。
- `email` が `DEFAULT_EMAIL` と異なる場合、更新。

### 3.2 seed_default_presets()

- 出勤プリセットが 0 件の場合に 2 件シード:
  - id=1: 9:00-18:00（休憩 12:00-13:00）
  - id=2: 8:30-17:30（休憩 12:00-13:00）

### 3.3 seed_default_categories()

- 非推奨カテゴリ（id=1〜6）を削除
- 不足カテゴリ（id=7〜22）を追加：その他, OWVIS(ライト), OPAS 等 16 件
- シーケンス値の自動調整

## 4. マイグレーション管理

スキーマの変更は **Alembic** で管理されている。マイグレーションコマンドは [CLAUDE.md](../CLAUDE.md) の Quick Commands を参照。

| 項目 | 値 |
|------|-----|
| 設定ファイル | `alembic.ini`, `alembic/env.py` |
| マイグレーションディレクトリ | `alembic/versions/` |
| 現在のヘッド | `de30cd662868` |

### マイグレーション全履歴

| # | リビジョン | 説明 | 主な内容 |
|---|-----------|------|----------|
| 1 | `53797f9c29e5` | initial schema | users, todos, attendances, tasks, task_time_entries, logs, presence_statuses, presence_logs テーブル作成 |
| 2 | `7e3eabbd85e8` | add password_hash to users | users に password_hash カラム追加 |
| 3 | `86da56d0b359` | add visibility to todos | todos に visibility カラム追加 |
| 4 | `29148e04951a` | add presence tables | presence 関連テーブル追加 |
| 5 | `c3790ffa7e38` | add daily_reports table | daily_reports テーブル追加 |
| 6 | `6ee8442a6984` | add log_sources table | log_sources テーブル追加 |
| 7 | `82739a6351f7` | add alert_rules and alerts tables | alert_rules, alerts テーブル追加 |
| 8 | `47696373217f` | add role to users | users に role カラム追加 |
| 9 | `05d4971bc34d` | add break fields to attendances | attendances に休憩フィールド追加 |
| 10 | `620335984593` | add attendance_presets and user default_preset_id | attendance_presets テーブル追加、users に default_preset_id 追加 |
| 11 | `fa32f8e03649` | add input_type to attendances | attendances に input_type カラム追加 |
| 12 | `a1b2c3d4e5f6` | add attendance_breaks table | attendance_breaks テーブル追加 |
| 13 | `e3a82a9fcd2f` | remove daily_report unique constraint | daily_reports の UNIQUE 制約削除 |
| 14 | `d58961695bbb` | add report to tasks | tasks に report フラグ追加 |
| 15 | `709a8464bb48` | add category_id task_name time_minutes to daily_reports | daily_reports にカテゴリ・タスク名・作業時間追加 |
| 16 | `b3f1a2c4d5e6` | rename username to email | users の username を email にリネーム |
| 17 | `c4d5e6f7a8b9` | add backlog_ticket_id to tasks | tasks に backlog_ticket_id 追加 |
| 18 | `d5e6f7a8b9c0` | add category_id to tasks | tasks に category_id 追加、task_categories テーブル追加 |
| 19 | `72671cad997f` | add task_list_items and source_item_id | task_list_items テーブル追加、tasks に source_item_id 追加 |
| 20 | `4f88001d4f7c` | remove parent_id from task_list_items | task_list_items から parent_id 削除 |
| 21 | `fe250895e6da` | add_calendar_tables | calendar_events, calendar_event_attendees, calendar_event_exceptions, calendar_reminders, user_calendar_settings テーブル追加 |
| 22 | `3b21411eef32` | add_calendar_rooms_and_room_id | calendar_rooms テーブル追加、calendar_events に room_id 追加 |
| 23 | `f65f9288d390` | add groups and user.group_id | groups テーブル追加、users に group_id 追加 |
| 24 | `01ac57c0d3d4` | auth_security_enhancement | login_attempts, auth_audit_logs テーブル追加、users に locked_until, session_version 追加 |
| 25 | `460b1c6d8e8f` | oauth_support | oauth_providers, user_oauth_accounts, oauth_states テーブル追加 |
| 26 | `a943bf44ce3b` | add_password_reset_tokens | password_reset_tokens テーブル追加 |
| 27 | `a5dceaeb239f` | add_user_preferred_locale | users に preferred_locale カラム追加 |
| 28 | `3c7419e092cb` | log_collection_v2_redesign | log_sources 再設計、log_files, log_entries テーブル追加 |
| 29 | `b8f2a1c3d4e5` | add_log_source_paths | log_source_paths テーブル追加、log_files に path_id 追加 |
| 30 | `0d0894c74444` | add_log_source_alert_on_change | log_sources に alert_on_change カラム追加 |
| 31 | `c1a2b3d4e5f6` | replace_server_name_with_group_id | log_sources の server_name → group_id に置換 |
| 32 | `2509bc83417f` | add_backlog_ticket_id_to_daily_reports | daily_reports に backlog_ticket_id 追加 |
| 33 | `6ddf43a20423` | add_unique_constraint_attendances_user_date | attendances に UNIQUE(user_id, date) 制約追加 |
| 34 | `b3df810d3406` | add_site_links | site_groups, site_links テーブル追加 |
| 35 | `a1c2d3e4f5b6` | add_wiki_pages | wiki_categories, wiki_tags, wiki_page_tags, wiki_pages テーブル追加 |
| 36 | `b2c3d4e5f6a7` | add_wiki_task_links | wiki_page_task_items, wiki_page_tasks テーブル追加 |
| 37 | `c3d4e5f6a7b8` | wiki_content_to_markdown | wiki_pages.content を JSON → TEXT に変換（Tiptap → Markdown）、yjs_state カラム削除 |
| 38 | `d4e5f6a7b8c9` | add_wiki_attachments | wiki_attachments テーブル追加 |
| 39 | `f8e8afae33a0` | add_indexes | todos, tasks, task_list_items, daily_reports, presence_logs に user_id/assignee_id/created_by インデックス追加 |
| 40 | `4671c277afb4` | wiki_visibility_local_public_private | wiki_pages.visibility を local/public/private 体系に変更（server_default: internal → local） |
| 41 | `8868b471d6cb` | add_departments_table | departments テーブル追加（階層構造: parent_id 自己参照、is_active フラグ） |
| 42 | `a9b8c7d6e5f4` | users_group_id_to_department_id | users.group_id → users.department_id にリネーム、FK を groups → departments に変更 |
| 43 | `b7c8d9e0f1a2` | migrate_groups_to_departments | groups データを departments にコピー、log_sources.group_id → department_id にリネーム・FK 付け替え、groups テーブル削除 |
| 44 | `08089f89ae62` | add_rbac_and_menus | roles, role_permissions, user_roles, menus, role_menus, user_menus テーブル追加 |
| 45 | `927e937218ac` | add_rbac_menu_id_indexes | roles, role_permissions, user_roles, menus, role_menus, user_menus に追加インデックス付与 |
| 46 | `057d0e1960cf` | add_department_menus | department_menus テーブル追加 |
| 47 | `de30cd662868` | add_department_menus_menu_id_index | department_menus, role_menus, user_menus に menu_id インデックス追加 |
