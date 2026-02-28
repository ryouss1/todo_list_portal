# ISSUE3: ソースコード 課題一覧（パフォーマンス・拡張性・規約・ハードコーディング・不整合）

> 作成日: 2026-02-25
> 対象バージョン: Alembic head `b3df810d3406` (add_site_links)

---

## 概要

現時点のソースコードについて、パフォーマンス・拡張性・コーディング規約・ハードコーディング・コード間不整合の観点から発見された課題をまとめる。セキュリティ観点の課題は `docs/issue2.md` に記載済みのため除外する。

---

## 課題一覧

### ISSUE-3-01: LogSource ステータス一覧取得の N+1 クエリ

**発見箇所:** `app/services/log_source_service.py` (list_source_statuses / _to_response_dict)
**優先度:** 高（パフォーマンス）
**状態:** ✅ 解決済み（2026-02-25）

**内容:**
`list_source_statuses()` はループ内で全ソースに対してクエリを発行し、かつ `_to_response_dict()` と `list_sources()` が `_build_group_map(db)` を毎回呼んで全グループを再取得する。

```python
# log_source_service.py
def list_source_statuses(db: Session) -> List[dict]:
    sources = crud_log_source.get_log_sources(db)
    result = []
    for source in sources:                                               # N ソース
        counts = crud_log_file.count_files_by_source(db, source.id)    # +1 クエリ/ソース
        paths = crud_path.get_paths_by_source(db, source.id)           # +1 クエリ/ソース
        if has_alert:
            for p in paths:
                crud_log_file.get_changed_files_by_path(db, p.id)      # +1 クエリ/パス

def _to_response_dict(db: Session, source: LogSource) -> dict:
    group_map = _build_group_map(db)   # ← 呼び出しのたびに全グループ再取得
```

**影響範囲:** ソース数・パス数が多い場合に応答時間が指数的に悪化。

**解決内容:**
- `_build_group_map(db)` を各関数の冒頭で1回だけ呼び、`_to_response_dict()` に引数渡しに変更
- `crud_log_file.count_files_by_source_bulk(db, source_ids)` を新設し一括集計
- `crud_log_file.get_changed_files_bulk(db, path_ids)` を新設しpath別bulk取得
- `list_sources()` / `list_source_statuses()` を group_map・counts・paths を事前bulk取得するよう改修

---

### ISSUE-3-02: Presence 全件取得の N+1 + 非アクティブユーザー混入

**発見箇所:** `app/services/presence_service.py:30-62`
**優先度:** 高（パフォーマンス・バグ）
**状態:** ✅ 解決済み（2026-02-25）

**内容:**
`get_all_statuses()` は全ユーザー・全プレゼンス・全 in_progress タスクを3本の独立クエリで取得し、Python 側でマージしている。`is_active=False` のユーザー（退職者など）も一覧に含まれるバグも潜在する。

**解決内容:**
- `crud_user.get_users(db, active_only=True)` を追加し非アクティブユーザーを除外
- `crud_task.get_in_progress_with_backlog(db)` CRUD関数を新設しCRUDバイパスを解消

---

### ISSUE-3-03: LogSource スキャン時のファイル Upsert N+1 クエリ

**発見箇所:** `app/services/log_source_service.py` (scan_source 内のファイルループ)
**優先度:** 高（パフォーマンス）
**状態:** ✅ 解決済み（2026-02-25）

**内容:**
`scan_source()` のファイル upsert ループでリモートファイル1件ごとに `get_file_by_path_and_name()` を SELECT している。パス配下に100ファイルあれば最低100 SELECT が発生する。

**解決内容:**
- ループ前に `{file_name: LogFile}` のdictをbulk取得し、`dict.get()` でルックアップするよう変更（N+1 → 1クエリ）

---

### ISSUE-3-04: 主要テーブルの user_id インデックス欠落

**発見箇所:** `app/models/todo.py`, `app/models/task.py`, `app/models/daily_report.py`, `app/models/presence.py`, `app/models/task_list_item.py`
**優先度:** 高（パフォーマンス）
**状態:** ✅ 解決済み（2026-02-25）

**内容:**
最も頻繁にフィルタされる `user_id` FK にインデックスが付いていないモデルが複数ある。

**解決内容:**
`todos.user_id`, `tasks.user_id`, `daily_reports.user_id`, `presence_logs.user_id` に `index=True` を追加し Alembic migration を作成。

---

### ISSUE-3-05: 勤怠・タスクリストの date/assignee_id 範囲検索インデックス欠落

**発見箇所:** `app/models/attendance.py`, `app/models/task_list_item.py`
**優先度:** 中（パフォーマンス）
**状態:** ✅ 解決済み（2026-02-25）

**内容:**
`attendances.date` 単独インデックス欠落、`task_list_items.assignee_id` / `created_by` にインデックスがない。

**解決内容:**
`attendances.date` に単独 `Index` を追加、`task_list_items.assignee_id` / `created_by` に `index=True` を追加し Alembic migration を作成。

---

### ISSUE-3-06: SiteLink / LogFile ステータス文字列のハードコーディング

**発見箇所:** `app/services/site_link_service.py`, `app/services/log_source_service.py`, `app/crud/site_link.py`
**優先度:** 中（ハードコーディング・保守性）
**状態:** ✅ 解決済み（2026-02-25）

**解決内容:**
`app/constants.py` に `class SiteLinkStatus` / `class LogFileStatus` を追加。各サービス・CRUDのリテラル文字列を定数に置き換え。

---

### ISSUE-3-07: アクセスプロトコル分岐のハードコーディング（拡張性欠如）

**発見箇所:** `app/services/log_source_service.py` (`_generate_folder_link`), `app/services/remote_connector.py` (`create_connector`)
**優先度:** 中（拡張性）
**状態:** ✅ 解決済み（2026-02-25）

**解決内容:**
`app/constants.py` に `class AccessMethod` を追加し、各サービス・コネクターのリテラル `"ftp"` / `"smb"` を定数に置き換え。未知プロトコルで明示的に `ValueError` を raise する。

---

### ISSUE-3-08: CRUD レイヤーのバイパス（直接 DB クエリ）

**発見箇所:** `app/services/attendance_service.py:246-270`, `app/services/summary_service.py:65`
**優先度:** 中（コーディング規約）
**状態:** ✅ 解決済み（2026-02-25）

**解決内容:**
- `attendance_service.py`: `db.query(User)` を `crud_user.get_user()` に統一
- `attendance_break.py` に `delete_breaks_by_attendance_id()` を新設し、サービス内の直接 `db.query(AttendanceBreak).delete()` を解消
- `summary_service.py`: `db.query(TaskCategory)` を `crud_task_category.get_all_categories()` に置き換え

---

### ISSUE-3-09: ロール文字列ハードコーディング（UserRole 定数未使用）

**発見箇所:** `app/services/site_link_service.py:154`
**優先度:** 中（ハードコーディング）
**状態:** ✅ 解決済み（2026-02-25）

**解決内容:**
`site_link_service.py` の `user.role == "admin"` を `user.role == UserRole.ADMIN` に統一。遅延インポートをモジュールトップに移動。

---

### ISSUE-3-10: done_task / batch_done の日報生成ロジック重複

**発見箇所:** `app/services/task_service.py:146-161`, `app/services/task_service.py:213-233`
**優先度:** 中（コーディング規約・保守性）
**状態:** ✅ 解決済み（2026-02-25）

**解決内容:**
`_build_daily_report_data(task: Task, report_date: date) -> DailyReportCreate` を切り出し、`done_task()` と `batch_done()` の両方から呼び出すよう変更。

---

### ISSUE-3-11: ログアラートの表示行数マジックナンバー

**発見箇所:** `app/services/log_source_service.py` (scan_source 内のアラート生成処理)
**優先度:** 中（ハードコーディング）
**状態:** ✅ 解決済み（2026-02-25）

**解決内容:**
`app/config.py` に `LOG_ALERT_CONTENT_DISPLAY_LINES: int = int(os.environ.get("LOG_ALERT_CONTENT_DISPLAY_LINES", "50"))` を追加し、2箇所のハードコード `50` を定数に置き換え。

---

### ISSUE-3-12: ファイルパターンのデフォルト値重複定義

**発見箇所:** `app/schemas/log_source.py`, `app/services/log_source_service.py` (`_reconcile_paths`)
**優先度:** 低（ハードコーディング）
**状態:** ✅ 解決済み（2026-02-25）

**内容:**
ログソースパスのデフォルト `file_pattern = "*.log"` がスキーマと `_reconcile_paths()` の両方に定義されており、将来デフォルトを変更した際に2箇所の修正が必要になる。

**解決内容:**
`app/constants.py` に `DEFAULT_LOG_FILE_PATTERN: str = "*.log"` を追加。`schemas/log_source.py` の2箇所と `log_source_service.py` の2箇所を定数参照に統一。

---

### ISSUE-3-13: AlertSeverity の三重定義

**発見箇所:** `app/schemas/alert.py:8`, `app/constants.py:51-57`
**優先度:** 低（不整合）
**状態:** ✅ 解決済み（2026-02-25）

**内容:**
アラート重要度の値が `ALERT_SEVERITIES` タプル（スキーマ）、`class AlertSeverity`（定数クラス）、`AlertSeverityType` Literal（型エイリアス）の3箇所で管理されていた。

**解決内容:**
`schemas/alert.py` から `ALERT_SEVERITIES = ("info", "warning", "critical")` を削除。`AlertSeverityType` Literal と `class AlertSeverity` による2箇所定義に統一。

---

### ISSUE-3-14: LOG_SOURCE_TYPES が config.py の可変 list として定義

**発見箇所:** `app/config.py` (LOG_SOURCE_TYPES)
**優先度:** 低（不整合・設計）
**状態:** ✅ 解決済み（2026-02-25）

**内容:**
`LOG_SOURCE_TYPES = ["WEB", "HT", "BATCH", "OTHER"]` が `AppConfig` クラスの設定値として可変 `list` で定義されていた。

**解決内容:**
- `app/config.py` から `LOG_SOURCE_TYPES` を削除
- `app/constants.py` の `class LogSourceType` を使用（ISSUE-3-06 で追加済み）
- `schemas/log_source.py` に `_VALID_SOURCE_TYPES` タプルを追加し、バリデーション箇所を `LogSourceType` 定数参照に変更

---

### ISSUE-3-15: api_presence.py の未使用 BackgroundTasks 引数

**発見箇所:** `app/routers/api_presence.py` (update_status)
**優先度:** 低（コーディング規約）
**状態:** ✅ 解決済み（2026-02-25）

**内容:**
`update_status()` ルーターが `BackgroundTasks` を引数として受け取っているが実際には使用していなかった。

**解決内容:**
`BackgroundTasks` インポートと `background_tasks: BackgroundTasks` 引数を削除。

---

### ISSUE-3-16: log_source_service.py の設定インポートが関数内遅延インポート

**発見箇所:** `app/services/log_source_service.py` (scan_source)
**優先度:** 低（コーディング規約）
**状態:** ✅ 解決済み（2026-02-25）

**内容:**
`scan_source()` 内で設定定数を関数スコープで遅延インポートしていた。

**解決内容:**
`LOG_SCAN_PATH_TIMEOUT`, `LOG_ALERT_CONTENT_MAX_LINES`, `LOG_ALERT_CONTENT_DISPLAY_LINES` をモジュールトップの `from app.config import ...` に移動。

---

### ISSUE-3-17: schemas/site_link.py の関数内 import re

**発見箇所:** `app/schemas/site_link.py` (field_validator 内)
**優先度:** 低（コーディング規約）
**状態:** ✅ 解決済み（2026-02-25）

**内容:**
`site_link.py` の `field_validator` 内で `import re` を毎回インポートしていた。

**解決内容:**
ファイル冒頭に `import re` を移動し、両 `validate_color` メソッド内の遅延 `import re` を削除。

---

### ISSUE-3-18: summary_service.py の非アクティブユーザー混入

**発見箇所:** `app/services/summary_service.py:54`
**優先度:** 中（バグリスク）
**状態:** ✅ 解決済み（2026-02-25）

**内容:**
`get_summary()` が非アクティブユーザーを含めてサマリーを生成していた。

**解決内容:**
`crud_user.get_users(db, active_only=True)` を使用するよう変更（ISSUE-3-08 と同時対応）。

---

### ISSUE-3-19: Wiki 関連 visibility 文字列リテラルの残存

**発見箇所:** `app/crud/wiki_page.py`, `app/schemas/wiki.py`
**優先度:** 低（ハードコーディング・保守性）
**状態:** ✅ 解決済み（2026-02-25）

**内容:**
`WikiPageVisibility` クラス追加後もCRUDクエリやスキーマのデフォルト値に文字列リテラルが残存していた。

**解決内容:**
- `crud/wiki_page.py`: `WikiPageVisibility` をインポートし、`["public", "internal"]` リテラルを `[WikiPageVisibility.PUBLIC, WikiPageVisibility.INTERNAL]` に置き換え（2箇所）
- `schemas/wiki.py`: `WikiPageVisibility` をインポートし、`visibility: str = "internal"` を `visibility: str = WikiPageVisibility.INTERNAL` に変更

---

### ISSUE-3-20: ログソース / サイトリンクの連続エラー上限がハードコーディング

**発見箇所:** `app/services/log_source_service.py`, `app/services/site_checker.py`
**優先度:** 低（ハードコーディング）
**状態:** ✅ 解決済み（2026-02-25）

**内容:**
サイトリンクのヘルスチェック失敗判定の閾値が設定外だった。

**解決内容:**
`app/config.py` に `SITE_MAX_CONSECUTIVE_FAILURES: int = int(os.environ.get("SITE_MAX_CONSECUTIVE_FAILURES", "5"))` を追加し、環境変数で制御可能に。

---

## 対応優先度まとめ

| ID | タイトル | 優先度 | カテゴリ | 状態 |
|----|---------|--------|---------|------|
| ISSUE-3-01 | LogSource ステータス一覧の N+1 クエリ | **高** | パフォーマンス | ✅ 解決済み |
| ISSUE-3-02 | Presence 全件取得の N+1 + 非アクティブ混入 | **高** | パフォーマンス・バグ | ✅ 解決済み |
| ISSUE-3-03 | LogSource スキャン時のファイル Upsert N+1 | **高** | パフォーマンス | ✅ 解決済み |
| ISSUE-3-04 | 主要テーブルの user_id インデックス欠落 | **高** | パフォーマンス | ✅ 解決済み |
| ISSUE-3-05 | 勤怠・タスクリストの date/assignee_id インデックス欠落 | 中 | パフォーマンス | ✅ 解決済み |
| ISSUE-3-06 | SiteLink / LogFile ステータス文字列ハードコーディング | 中 | ハードコーディング | ✅ 解決済み |
| ISSUE-3-07 | アクセスプロトコル分岐ハードコーディング | 中 | 拡張性 | ✅ 解決済み |
| ISSUE-3-08 | CRUD レイヤーのバイパス | 中 | コーディング規約 | ✅ 解決済み |
| ISSUE-3-09 | ロール文字列ハードコーディング（UserRole 未使用） | 中 | ハードコーディング | ✅ 解決済み |
| ISSUE-3-10 | done_task / batch_done の日報生成ロジック重複 | 中 | コーディング規約 | ✅ 解決済み |
| ISSUE-3-11 | ログアラート表示行数マジックナンバー `50` | 中 | ハードコーディング | ✅ 解決済み |
| ISSUE-3-12 | ファイルパターンデフォルト値の重複定義 | 低 | ハードコーディング | ✅ 解決済み |
| ISSUE-3-13 | AlertSeverity の三重定義 | 低 | 不整合 | ✅ 解決済み |
| ISSUE-3-14 | LOG_SOURCE_TYPES が config.py の可変 list | 低 | 不整合・設計 | ✅ 解決済み |
| ISSUE-3-15 | api_presence.py の未使用 BackgroundTasks 引数 | 低 | コーディング規約 | ✅ 解決済み |
| ISSUE-3-16 | log_source_service.py の設定遅延インポート | 低 | コーディング規約 | ✅ 解決済み |
| ISSUE-3-17 | schemas/site_link.py の関数内 import re | 低 | コーディング規約 | ✅ 解決済み |
| ISSUE-3-18 | summary_service.py の非アクティブユーザー混入 | 中 | バグリスク | ✅ 解決済み |
| ISSUE-3-19 | Wiki visibility 文字列リテラルの残存 | 低 | ハードコーディング | ✅ 解決済み |
| ISSUE-3-20 | サイトリンク連続失敗閾値のハードコーディング | 低 | ハードコーディング | ✅ 解決済み |
