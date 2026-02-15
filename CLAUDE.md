# Todo List Portal - Development Guide

このプロジェクトは TodoListを管理するアプリケーションです。

機能追加、修正の際、ドキュメントに計画を記載し開発を行って下さい。
UNITテストを実施してください。

機能に不明点がある場合 @docs/QUESTION1.mdから順次記載して確認してください。
課題などが発覚した場合も docs/ISSUE1.mdから順次記載してください。

開発の際には、拡張性、モジュールの再利用性を重視して開発してください。
SQLの単体テストも将来行えるようにしてください。

技術的負債は必ず資料に記載してください。技術的負債は可能な限り減らして
以下の資料が各機能概要の資料となります。機能追加の際にはこの資料を更新してください

# 基本ルール
- Python は ruff でフォーマット
- テストは pytest、`make test` で実行
- コミットメッセージは conventional commits

# 詳細ドキュメント（必要時に参照）
- 設計書 : @docs/spec.md
- API設計: @docs/api-design.md
- API設計: @docs/api-design-endpoint.md
- DB設計: @docs/db-schema.md
- デプロイ手順: @docs/deploy.md
@docs/spec_function.md
@docs/spec_nonfunction.md

開発時には、@docs/api/[endpoint]/*.md のファイルを参照して開発してください。

各画面仕様

各画面の仕様は api_endpoint毎にフォルダを作成しそこに設計書を作成する。

@docs/api/[api_endpoint]/
@docs/ws/[websoket_endpoint]/

## Quick Commands

```bash
# Dev server
python main.py

# Tests
pytest tests/ -q

# Lint + Format
ruff check --fix . && ruff format .

# DB migration (after model changes)
alembic revision --autogenerate -m "description"
alembic upgrade head
```

## Architecture

**Routers** (thin HTTP wrappers) → **Services** (business logic) → **CRUD** (DB access) → **Models**

- Services raise `NotFoundError` / `ConflictError` / `AuthenticationError` (never `HTTPException`)
- Routers convert exceptions to HTTP responses via `app_error_handler`
- `app/core/deps.py`: `get_current_user_id(request)` reads session, used via `Depends()`
- JS layer: `common.js` (escapeHtml, formatTime, showToast) → `api.js` (fetch wrapper) → page-specific JS

### Models

| Model | Table | Key Fields |
|-------|-------|------------|
| `User` | `users` | email, display_name, password_hash, role (admin/user) |
| `Todo` | `todos` | user_id, title, priority, is_completed, visibility (private/public) |
| `Attendance` | `attendances` | user_id, date, clock_in, clock_out, input_type |
| `AttendanceBreak` | `attendance_breaks` | attendance_id (FK CASCADE), break_start, break_end |
| `Task` | `tasks` | user_id, title, status, category_id (FK), time_entries, backlog_ticket_id, source_item_id (FK) |
| `TaskListItem` | `task_list_items` | title, assignee_id, created_by, parent_id (CASCADE), status, total_seconds, category_id |
| `Log` | `logs` | level, message, source |
| `PresenceStatus` | `presence_statuses` | user_id (UNIQUE), status, message |
| `PresenceLog` | `presence_logs` | user_id, status, message, changed_at |
| `TaskCategory` | `task_categories` | name (master data for report categories) |
| `DailyReport` | `daily_reports` | user_id, report_date, category_id (FK), task_name, time_minutes, work_content |
| `LogSource` | `log_sources` | name, file_path, system_name, parser_pattern, polling_interval_sec |
| `AlertRule` | `alert_rules` | name, condition (JSON), alert_title_template, severity |
| `Alert` | `alerts` | title, message, severity, rule_id (FK), acknowledged, acknowledged_by |

### Services

| Service | Purpose |
|---------|---------|
| `log_service` | System log queries + alert rule evaluation on create |

## Auth

- Session-based: `SessionMiddleware` (signed cookie with `SECRET_KEY`)
- Public paths: `/login`, `/static/*`, `/api/auth/*`, `/ws/*`
- Public API: `POST /api/logs/` (external log ingestion)
- Login: `POST /api/auth/login` → sets `session["user_id"]`
- `api.js` redirects to `/login` on 401

## Conventions

- Python 3.9: use `Optional[str]` not `str | None`
- isort: `known-first-party = ["app"]`
- Double quotes for strings
- passlib + bcrypt < 4.1 (compatibility requirement)

## 設定管理
- 全設定は `app/config.py` に集約。`python-dotenv` でプロジェクトルートの `.env` を自動読み込み
- 機密情報（`DATABASE_URL`, `SECRET_KEY`, `DEFAULT_PASSWORD`, `SMTP_PASSWORD` 等）はコードにデフォルト値を持たない → `.env` ファイルで設定必須
- `.env` は `.gitignore` に登録済み（Git管理外）
- パスワード・接続情報の確認は `.env` ファイルを参照してください

## Alembic

- Current head: `f65f9288d390` (add groups and user.group_id)
- Migration chain: initial(`53797f9c29e5`) → ... → add_task_list_items(`72671cad997f`) → remove_parent_id(`4f88001d4f7c`) → calendar_tables(`fe250895e6da`) → calendar_rooms(`3b21411eef32`) → groups(`f65f9288d390`)
- `env.py` reads `DATABASE_URL` from `app.config` and imports `app.models`
