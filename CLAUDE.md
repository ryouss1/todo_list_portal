# Todo List Portal - Development Guide

このプロジェクトは TodoListを管理するアプリケーションです。

機能追加、修正の際、ドキュメントに計画を記載し開発を行って下さい。
UNITテストを実施してください。

機能に不明点がある場合 @docs/QUESTIONx.mdを作成してください。xは最大の番号となります。
課題などが発覚した場合も docs/ISSUEx.mdを作成してください。

開発の際には、拡張性、モジュールの再利用性を重視して開発してください。
SQLの単体テストも将来行えるようにしてください。
技術的負債は必ず資料に記載してください。技術的負債は可能な限り減らしてください。

# 基本ルール
- Python は ruff でフォーマット
- テストは pytest（`pytest tests/ -q`）
- コミットメッセージは conventional commits

# 詳細ドキュメント（必要時に参照）
- 設計書: @docs/spec.md
- API設計: @docs/api-design.md
- エンドポイント一覧: @docs/api-design-endpoint.md
- DB設計: @docs/db-schema.md
- 機能仕様: @docs/spec_function.md
- 非機能要件: @docs/spec_nonfunction.md
- デプロイ手順: @docs/deploy.md
- 画面別設計: @docs/api/[api_endpoint]/ , @docs/ws/[websocket_endpoint]/

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

全モデル定義は [db-schema.md](docs/db-schema.md) を参照。主要テーブル:

`users`, `todos`, `attendances`, `attendance_breaks`, `tasks`, `task_time_entries`, `task_list_items`, `task_categories`, `daily_reports`, `logs`, `log_sources`, `presence_statuses`, `presence_logs`, `alerts`, `alert_rules`, `calendar_events`, `calendar_rooms`, `groups`, `oauth_providers`, `user_oauth_accounts`, `password_reset_tokens`

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

- Current head: `6ddf43a20423` (add_unique_constraint_attendances_user_date)
- Migration chain: initial(`53797f9c29e5`) → ... → groups(`f65f9288d390`) → auth_security(`01ac57c0d3d4`) → oauth(`460b1c6d8e8f`) → password_reset(`a943bf44ce3b`) → preferred_locale(`a5dceaeb239f`) → log_v2(`3c7419e092cb`) → log_source_paths(`b8f2a1c3d4e5`) → alert_on_change(`0d0894c74444`) → group_id(`c1a2b3d4e5f6`) → daily_report_backlog(`2509bc83417f`) → attendance_unique(`6ddf43a20423`)
- `env.py` reads `DATABASE_URL` from `app.config` and imports `app.models`
