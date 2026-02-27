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
- テストは pytest（アプリ: `pytest tests/ -q`、コア: `cd portal_core && pytest tests/ -q`）
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

# Tests (app-specific: ~584 tests)
pytest tests/ -q

# Tests (portal_core: ~158 tests)
cd portal_core && pytest tests/ -q && cd ..

# Tests (all)
cd portal_core && pytest tests/ -q && cd .. && pytest tests/ -q

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
- JS layer: `common.js` (escapeHtml, formatTime, showToast) → `api.js` (fetch wrapper) → `app_common.js` (getCategories等アプリ固有) → page-specific JS

### Models

全モデル定義は [db-schema.md](docs/db-schema.md) を参照。全41テーブル:

`users`, `groups`, `login_attempts`, `auth_audit_logs`, `oauth_providers`, `user_oauth_accounts`, `oauth_states`, `password_reset_tokens`, `todos`, `attendances`, `attendance_breaks`, `attendance_presets`, `tasks`, `task_time_entries`, `task_categories`, `task_list_items`, `daily_reports`, `logs`, `log_sources`, `log_source_paths`, `log_files`, `log_entries`, `presence_statuses`, `presence_logs`, `alerts`, `alert_rules`, `calendar_events`, `calendar_event_exceptions`, `calendar_event_attendees`, `calendar_rooms`, `calendar_reminders`, `user_calendar_settings`, `site_groups`, `site_links`, `wiki_categories`, `wiki_tags`, `wiki_pages`, `wiki_page_tags`, `wiki_page_task_items`, `wiki_page_tasks`, `wiki_attachments`

## Auth

- Session-based: `SessionMiddleware` (signed cookie with `SECRET_KEY`)
- Public paths: `/login`, `/static/*`, `/api/auth/*`, `/ws/*`
- Public API: `POST /api/logs/` (external log ingestion)
- Login: `POST /api/auth/login` → sets `session["user_id"]`
- `api.js` redirects to `/login` on 401
- CSRF: `fastapi-csrf-protect` (Double Submit Cookie pattern) — POST/PUT/PATCH/DELETE は `X-CSRF-Token` ヘッダー必須。除外: `/api/auth/`, `/api/logs/`
- `register_csrf_exempt(prefix)`: 追加の CSRF 除外プレフィックスを登録

## Conventions

- Python 3.9: use `Optional[str]` not `str | None`
- isort: `known-first-party = ["app", "portal_core"]`
- Double quotes for strings
- passlib + bcrypt < 4.1 (compatibility requirement)

## 設定管理
- 全設定は `app/config.py` に集約。`CoreConfig`（共通基盤）→ `AppConfig(CoreConfig)`（アプリ固有）のクラス継承構造
- `globals()` ループで後方互換維持: 既存の `from app.config import DATABASE_URL` はそのまま動作
- `python-dotenv` でプロジェクトルートの `.env` を自動読み込み
- 機密情報（`DATABASE_URL`, `SECRET_KEY`, `DEFAULT_PASSWORD`, `SMTP_PASSWORD` 等）はコードにデフォルト値を持たない → `.env` ファイルで設定必須
- `.env` は `.gitignore` に登録済み（Git管理外）
- パスワード・接続情報の確認は `.env` ファイルを参照してください

## 定数管理
- コア定数（`UserRole`, `UserRoleType`）: `portal_core/portal_core/core/constants.py`（`app/core/constants.py` は再エクスポートshim）
- アプリ固有定数（`TaskStatus`, `ItemStatus`, `PresenceStatusValue`, `InputType`, `AlertSeverity`, `WikiPageVisibility`）: `app/constants.py`

## ナビゲーション
- `portal_core/portal_core/app_factory.py` の `PortalApp` がコアナビ項目（Dashboard, Users）を自動登録
- `main.py` で `portal.register_nav_item(NavItem(...))` によりアプリ固有ナビ項目を登録
- `app_factory.py` の `_render()` が全テンプレートに `nav_items`, `app_title`, `extra_head_scripts` を自動注入
- `portal_core/portal_core/templates/base.html` は `{% for item in nav_items %}` ループで動的レンダリング

## テンプレート
- portal_core テンプレート（マスター）: `base.html`, `login.html`, `users.html`, `forgot_password.html`, `reset_password.html`, `_dashboard_base.html`
- アプリ側テンプレート: `templates/` に業務ページ17ファイルのみ（コアテンプレートの重複なし）
- ブランド: テンプレート内 `{{ app_title }}` は `_render()` が `PortalApp.title` から自動注入
- `register_head_script(path)`: アプリ固有のグローバルスクリプトを `base.html` の `<head>` に注入（例: `portal.register_head_script("/static/js/app_common.js")`）
- Jinja2 検索順: アプリ側 `templates/` → コア `portal_core/portal_core/templates/`

## 共通機能分離 (portal_core)
- 設計書: @docs/spec_common_separation.md
- フェーズ1（準備リファクタリング）: ✅ 完了
- フェーズ2（portal_core パッケージ作成）: ✅ 完了
- フェーズ3（テスト分離・安定化）: ✅ 完了（コア158テスト + アプリ584テスト = 742テスト）
- テンプレート重複解消: ✅ 完了（portal_core マスター化、アプリ側の重複5ファイル削除）
- エントリーポイント: `main.py` → `PortalApp(config).setup_core()` → `register_*()` → `build()`
- 後方互換: `app/` 配下に再エクスポートshimを配置、既存の `from app.xxx import` は全て動作継続
- 静的ファイル: コア → `/static/core/`、アプリ固有 → `/static/`
- テスト: コアテスト → `portal_core/tests/`（独立実行可）、アプリテスト → `tests/`

## WebSocket
- Heartbeat: `WS_PING_INTERVAL`（デフォルト30秒）間隔で ping を送信、`WS_PING_TIMEOUT`（デフォルト10秒）以内に pong がなければゾンビ接続と判定し切断
- 設定: `portal_core/portal_core/config.py` の `CoreConfig` に定義
- 実装: `portal_core/portal_core/app_factory.py` の `WebSocketManager`

## Alembic

- Current head: `4671c277afb4` (wiki_visibility_local_public_private)
- Migration chain: initial(`53797f9c29e5`) → ... → groups(`f65f9288d390`) → auth_security(`01ac57c0d3d4`) → oauth(`460b1c6d8e8f`) → password_reset(`a943bf44ce3b`) → preferred_locale(`a5dceaeb239f`) → log_v2(`3c7419e092cb`) → log_source_paths(`b8f2a1c3d4e5`) → alert_on_change(`0d0894c74444`) → group_id(`c1a2b3d4e5f6`) → daily_report_backlog(`2509bc83417f`) → attendance_unique(`6ddf43a20423`) → site_links(`b3df810d3406`) → wiki_pages(`a1c2d3e4f5b6`) → wiki_task_links(`b2c3d4e5f6a7`) → wiki_content_to_markdown(`c3d4e5f6a7b8`) → wiki_attachments(`d4e5f6a7b8c9`) → add_indexes(`f8e8afae33a0`) → wiki_visibility(`4671c277afb4`)
- `env.py` imports `portal_core.models` + `app.models`, reads `DATABASE_URL` from `app.config`
