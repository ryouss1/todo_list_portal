# システム改修履歴

> 本ドキュメントはマイグレーション日付・仕様書・実装記録をもとに再構成した改修履歴である。
> Git コミット履歴は `initial commit` / `2nd commit` の2件のみのため、Alembic マイグレーション日付を主軸とする。

---

## 2026-02-09

### 初期構築

- **プロジェクト立ち上げ**
  - FastAPI + SQLAlchemy + PostgreSQL + Uvicorn 構成で初期化
  - ログイン画面（メールアドレス + パスワード）、セッション認証
  - `users`, `todos`, `attendances`, `tasks`, `task_time_entries`, `logs` テーブル作成
  - `presence_statuses`, `presence_logs` テーブル作成（初期 migration に含む）
  - Alembic マイグレーション管理開始（`53797f9c29e5` initial schema）

- **追加**: `users.password_hash` カラム追加（`7e3eabbd85e8`）

---

## 2026-02-10

### 機能拡張 フェーズ1

- **Todo**: `visibility`（public/private）カラム追加、公開Todo一覧 API 追加（`86da56d0b359`）
- **在籍管理**: `presence_statuses`, `presence_logs` テーブル整備（`29148e04951a`）
- **日報管理**: `daily_reports` テーブル追加（`c3790ffa7e38`）
- **ログソース管理**: `log_sources` テーブル追加、FTP/SMB 接続情報管理（`6ee8442a6984`）
- **アラート管理**: `alert_rules`, `alerts` テーブル追加（`82739a6351f7`）
- **RBAC**: `users.role`（admin/user）カラム追加、`require_admin` 依存性注入（`47696373217f`）

### 勤怠管理 強化

- 休憩フィールド追加 → のちに `attendance_breaks` テーブルへ分離（`05d4971bc34d`）
- `attendance_presets` テーブル追加、`users.default_preset_id` 追加（`620335984593`）
- `attendances.input_type`（web/ic_card/admin）追加（`fa32f8e03649`）
- `attendance_breaks` テーブル正式作成（`a1b2c3d4e5f6`）

### タスク管理 強化

- `daily_reports` のUNIQUE制約削除（同一日の複数日報作成を許可）（`e3a82a9fcd2f`）
- `tasks.report` フラグ追加（Done時に日報自動作成）（`d58961695bbb`）
- `daily_reports` に `category_id`, `task_name`, `time_minutes` 追加（`709a8464bb48`）
- `users.username` → `users.email` にリネーム（`b3f1a2c4d5e6`）
- `tasks.backlog_ticket_id` 追加（Backlog チケット番号連携）（`c4d5e6f7a8b9`）
- `tasks.category_id` 追加、`task_categories` テーブル作成（`d5e6f7a8b9c0`）

---

## 2026-02-11

### タスクリスト・カレンダー追加

- **タスクリスト**: `task_list_items` テーブル追加、`tasks.source_item_id` 追加（バックログ管理）（`72671cad997f`）
- `task_list_items.parent_id` 削除（フラット構造に変更）（`4f88001d4f7c`）
- **カレンダー**: `calendar_events`, `calendar_event_attendees`, `calendar_event_exceptions`, `calendar_reminders`, `user_calendar_settings` テーブル追加（`fe250895e6da`）
- **会議室**: `calendar_rooms` テーブル追加、`calendar_events.room_id` 追加（`3b21411eef32`）
- **グループ管理**: `groups` テーブル追加、`users.group_id` 追加（`f65f9288d390`）

---

## 2026-02-13

### 認証セキュリティ強化・OAuth 対応

- **認証セキュリティ**:
  - `login_attempts` テーブル追加（ログイン試行記録）
  - `auth_audit_logs` テーブル追加（監査ログ）
  - `users.locked_until` 追加（アカウントロックアウト）
  - `users.session_version` 追加（セッション無効化）
  - パスワードポリシー、レート制限機能実装（`01ac57c0d3d4`）
  - 設計書: `docs/api/auth/security_enhancement.md`

- **OAuth2/SSO**:
  - `oauth_providers`, `user_oauth_accounts`, `oauth_states` テーブル追加
  - Authorization Code + PKCE フロー、Google/GitHub 対応（`460b1c6d8e8f`）
  - 設計書: `docs/api/auth/oauth.md`

- **パスワードリセット**:
  - `password_reset_tokens` テーブル追加
  - SHA-256 ハッシュのみ保存、SMTP 送信、レート制限（`a943bf44ce3b`）
  - 設計書: `docs/api/auth/password_reset.md`

---

## 2026-02-17

### 国際化 (i18n) 対応

- `users.preferred_locale`（ja/en）カラム追加（`a5dceaeb239f`）
- Babel + gettext によるサーバーサイド翻訳
- `static/locale/{locale}.json` によるフロントエンド翻訳
- `i18n.t()` 関数でクライアントサイド翻訳対応
- エラーメッセージを英語キーで管理し、`app_error_handler` で境界層翻訳

---

## 2026-02-18

### ログ収集 v2 再設計・各種改善

- **ログ収集 v2**:
  - `log_sources` テーブル再設計（`collection_mode`, `parser_pattern` 等追加）
  - `log_files`, `log_entries` テーブル追加（ファイル管理・行レベル取り込み）（`3c7419e092cb`）
  - 設計書: `docs/spec_log_function.md`

- **監視パス管理**:
  - `log_source_paths` テーブル追加（1ソースに複数パス設定可）
  - `log_files.path_id` 追加（`b8f2a1c3d4e5`）

- **ファイル変更通知**:
  - `log_sources.alert_on_change` カラム追加
  - スキャン時のタイムスタンプ変化を検出し自動アラート生成
  - フォルダリンク表示（SMB: `\\host\path`、FTP: `ftp://host/path`）（`0d0894c74444`）

- **グループ紐付け**:
  - `log_sources.server_name` → `log_sources.group_id` に変更（`c1a2b3d4e5f6`）

- **日報改善**:
  - `daily_reports.backlog_ticket_id` 追加（`2509bc83417f`）

- **勤怠制約追加**:
  - `attendances` に UNIQUE(user_id, date) 制約追加（同一日の重複出勤防止）（`6ddf43a20423`）

---

## 2026-02-19

### サイトリンク機能追加

- `site_groups`, `site_links` テーブル追加（`b3df810d3406`）
- サイト URL 登録、グループ管理、ヘルスチェック設定（間隔・タイムアウト・SSL検証）
- バックグラウンドチェッカー（`SITE_CHECKER_ENABLED=true`）
- WebSocket (`/ws/sites`) でリアルタイムステータス更新
- URL はレスポンスに含めず `/api/sites/{id}/url` エンドポイント経由のみ取得
- 設計書: `docs/api/sites/SPEC_sites.md`, `docs/screens/sites.md`

---

## 2026-02-22〜24

### portal_core 分離（共通基盤パッケージ化）

設計書: `docs/spec_common_separation.md`

#### フェーズ1（2026-02-22）: 準備リファクタリング

- `app/config.py` を `CoreConfig` → `AppConfig(CoreConfig)` 継承構造に変更、`globals()` ループで後方互換維持
- `UserRole`/`UserRoleType` を `app/core/constants.py` に整理、アプリ固有定数を `app/constants.py` に分離
- `seed_default_user()` を `app/core/init_db.py` に抽出
- `templates/base.html` のナビを `{% for item in nav_items %}` 動的ループに変更
- `getCategories()` を `static/js/common.js` から `static/js/app_common.js` に分離

#### フェーズ2（2026-02-22〜23）: portal_core パッケージ作成

- `portal_core/` ディレクトリ作成（pip パッケージ: `pip install -e portal_core/`）
- 共通モデル8つを `portal_core/portal_core/models/` に移動
  - User, Group, LoginAttempt, AuthAuditLog, OAuthProvider, UserOAuthAccount, OAuthState, PasswordResetToken
- `portal_core/portal_core/core/` に横断的関心事を移動（例外、セキュリティ、DI、ロギング、認証）
- 共通CRUD 9つ、共通スキーマ4つ、共通サービス7つ、共通ルーター4つを移動
- `PortalApp` ファクトリクラス作成（`setup_core()` → `register_*()` → `build()` パターン）
- `app/` 配下に再エクスポートshimを配置（既存の `from app.xxx import` が動作継続）
- `main.py` を `PortalApp(config).setup_core()` → `register_nav_item()` → `build()` に変更

#### フェーズ3（2026-02-23〜24）: テスト分離・安定化

- `portal_core/tests/` を新規作成、`core_app` フィクスチャで portal_core 単体テスト実行可能に
- コアテスト8ファイルを `portal_core/tests/` に移動・インポートパス修正
- `tests/conftest.py` のインポートパスを `portal_core.*` に更新
- テスト総数: **651件**（portal_core 151件 + アプリ 500件）全パス確認

#### テンプレート重複解消（2026-02-24）

- `portal_core/portal_core/templates/` の6ファイルをマスターとして確立
  - `base.html`, `login.html`, `users.html`, `forgot_password.html`, `reset_password.html`, `_dashboard_base.html`
- アプリ側の重複テンプレート5ファイルを削除
- `{{ app_title }}` を `PortalApp._render()` で自動注入
- `register_head_script()` API 追加（アプリ固有グローバルスクリプトを `<head>` に注入）

---

## 2026-02-25

### ログ出力の再設計（watchfiles ループ問題修正）

- **問題**: uvicorn `reload=True` + watchfiles がプロジェクトルートを監視するため、`app.log` への書き込みが無限ループを引き起こしていた
- **対応**:
  - ログ出力先を `app.log`（プロジェクトルート）から `logs/` ディレクトリに移動
  - ログを3ファイルに分離:
    | ファイル | 対象 | レベル |
    |---------|------|--------|
    | `logs/app.log` | アプリ全般（SQL 除く） | INFO + |
    | `logs/sql.log` | SQLAlchemy クエリ | DEBUG + |
    | `logs/error.log` | 全ロガーのエラー | ERROR + |
  - `portal_core/portal_core/config.py` に `LOG_DIR`, `SQL_LOG_LEVEL` 追加
  - `portal_core/portal_core/core/logging_config.py` を3ハンドラ・4ロガー構成に再設計
  - `main.py` に `reload_excludes=["*.log", "logs/"]` 追加
  - `docs/spec_nonfunction.md` ロギングセクション更新

### カレンダー セル選択動作修正

- **問題**: 月ビューでのセル選択時、FullCalendar が `allDay=true` / `end=翌日00:00` を渡すため時間入力モーダルが開かなかった
- **対応**: `static/js/calendar.js` の `select` コールバックを修正
  - 月ビュー（`dayGridMonth`）: 終日フラグを OFF にし、デフォルト 09:00〜10:00 でモーダルを開く
  - 週/日ビューの終日行: 終日イベントとして開く
  - 週/日ビューの時刻エリア: ドラッグ選択した時間範囲でモーダルを開く
- `docs/screens/calendar.md` にセル選択動作テーブルを追加
- `docs/api/calendar/SPEC_calendar.md` セクション 7.3 更新

### WIKI 機能 設計書 作成

- `docs/spec_wiki.md` を新規作成
- 初期採用方針:
  - エディタ: Tiptap v2（ProseMirror ベースのブロックエディタ）
  - リアルタイム共同編集: Yjs + ypy-websocket（CRDT ベース）
  - 検索: PostgreSQL FTS
- Yjs + Tiptap の詳細設計を記載（アーキテクチャ図、DB スキーマ、実装コード例）

### WIKI 機能 実装（フェーズ1）

- **設計変更**: Tiptap v2 → **Toast UI Editor** に切り替え（実装コスト削減、Markdown ネイティブ）
- **DB スキーマ追加**:
  - `wiki_categories`, `wiki_tags`, `wiki_pages`, `wiki_page_tags` テーブル追加（`a1c2d3e4f5b6`）
  - `wiki_page_task_items`, `wiki_page_tasks` テーブル追加（タスクリンク、`b2c3d4e5f6a7`）
  - `wiki_pages.content` を Tiptap JSON → Markdown TEXT に移行（`c3d4e5f6a7b8`）
- **API 実装**:
  - `GET/POST /api/wiki/pages/` — ページ CRUD + 階層ツリー + スラッグ検索
  - `PUT /api/wiki/pages/{id}/move` — 親変更（循環参照防止）
  - `PUT /api/wiki/pages/{id}/tags` — タグ一括更新
  - `GET/PUT /api/wiki/pages/{id}/tasks/*` — タスクリンク管理
  - `GET/POST/PUT/DELETE /api/wiki/categories/` — カテゴリ管理（admin）
  - `GET/POST/DELETE /api/wiki/tags/` — タグ管理
- **フロントエンド**:
  - `/wiki`, `/wiki/new`, `/wiki/{slug}`, `/wiki/{slug}/edit` 画面追加
  - Toast UI Editor（WYSIWYG / Markdown モード切替）
  - 階層ツリーサイドバー、タグ・カテゴリフィルタ
  - パンくずリスト自動生成
- **PostgreSQL FTS**: `tsvector` + GIN インデックス + DB トリガーによるタイトル全文検索
- テスト追加: `tests/test_wiki.py` 41件 → 総テスト数 **692件**（コア151 + アプリ541）

---

## 2026-02-26

### CSRF 保護強化

- **問題**: 旧実装（Origin/Referer ヘッダー検証のみ）は、ヘッダーを送らないリクエストをスルーする脆弱性があった
- **対応**: `fastapi-csrf-protect 1.0.7` を導入（**Double Submit Cookie パターン**）
  - `portal_core/portal_core/app_factory.py`: `@CsrfProtect.load_config` + `csrf_middleware` 差し替え + `_render()` でトークン生成
  - `portal_core/portal_core/templates/base.html`: `<meta name="csrf-token">` 追加
  - `portal_core/portal_core/static/js/api.js`: 全 state-changing リクエストに `X-CSRFToken` ヘッダー追加
  - CSRF 除外パス: `POST /api/logs/`（外部システム）、`/api/auth/` 配下、OAuth コールバック
  - テストフィクスチャ: `fastapi-csrf-token` Cookie + `X-CSRFToken` ヘッダーを `conftest.py` に追加
- `docs/spec_nonfunction.md` セキュリティセクション更新

### Wiki 添付ファイル DB 整備

- `wiki_attachments` テーブル追加（`d4e5f6a7b8c9`）
  - `page_id`, `filename`, `stored_path`, `mime_type`, `file_size`
  - `after_delete` イベントリスナーで物理ファイルも自動削除
  - 物理保存先: `uploads/wiki/{page_id}/`
- **現状**: DB・モデルのみ。添付ファイル API は未実装

### パフォーマンスインデックス追加

- 主要テーブルにクエリ用インデックスを追加（`f8e8afae33a0`）
  - `todos`: `(user_id, is_completed)`, `due_date`
  - `tasks`: `(user_id, status)`, `source_item_id`
  - `task_list_items`: `(assignee_id, status)`, `scheduled_date`
  - `daily_reports`: `(user_id, report_date)`, `report_date`
  - `presence_logs`: `(user_id, changed_at)`

### Wiki visibility 体系変更

- `wiki_pages.visibility` の値体系を整理（`4671c277afb4`）
  - 旧: `internal`（全ログイン）/ `public`（外部公開）/ `private`（作成者のみ）
  - 新: `local`（自部署・同一グループ、**デフォルト**）/ `public`（全ログインユーザー）/ `private`（作成者のみ）
  - server_default を `'internal'` → `'local'` に変更
  - 既存の `internal` / `public` レコードはすべて `public` に移行

### テスト増加・ドキュメント全面更新

- Wiki テスト追加（visibility 対応）: 41件 → 52件
- タスクリストテスト追加: 43件 → 46件
- **総テスト数: 706件**（portal_core 151件 + アプリ 555件）
- 更新ドキュメント一覧:
  - `CLAUDE.md` — テスト数、テーブル数、Alembic ヘッド、CSRF、`wiki_attachments`
  - `docs/spec.md` — tech stack に `fastapi-csrf-protect` 追加、テスト数、モデル数
  - `docs/spec_nonfunction.md` — CSRF 実装方式更新、テスト数更新
  - `docs/db-schema.md` — `wiki_attachments` テーブル定義追加、visibility 値更新、マイグレーション3件追加
  - `docs/api-design.md` — Wiki visibility デフォルト `"local"` に更新
  - `docs/spec_function.md` — Wiki visibility 3段階説明、ファイル添付行追加
  - `docs/report/history.md` — 本ドキュメント（今回更新）
- Alembic head: `c3d4e5f6a7b8` → `4671c277afb4`

### CSRF バグ修正

- **問題**: CSRF 導入後に `POST /api/task-list/` 等が 403 を返す事象が発生
- **原因1（ブラウザキャッシュ）**: ブラウザが CSRF 実装前の旧 `api.js`（`X-CSRF-Token` ヘッダーなし）をキャッシュしていた
  - **修正**: `portal_core/portal_core/templates/base.html` — `/static/core/js/api.js?v=2` にバージョンパラメータ追加
- **原因2（wiki.js が api wrapper 未使用）**: `static/js/wiki.js` の `wikiApi` が直接 `fetch()` を使っており、全 Wiki POST/PUT/DELETE リクエストで `X-CSRF-Token` ヘッダーが送信されていなかった
  - **修正**: `wikiApi` 全メソッドを `api.get()` / `api.post()` / `api.put()` / `api.del()` ラッパーに置き換え（CSRF + 401 リダイレクト対応を継承）

### Sites UI 改善

- **グループ削除ボタン追加**: グループ編集モーダルのフッターに Delete ボタンを追加（admin + 編集モード時のみ表示）
  - 削除時は確認ダイアログを表示。グループ内リンクは自動的に未分類へ移動
  - `templates/sites.html`: `#btn-delete-group` ボタン追加
  - `static/js/sites.js`: `openGroupModal()` に表示制御追加、`deleteGroup()` 関数追加
- **リンク追加ボタン UX 改善**: グループ行の「リンク追加」ボタンを小型の「+ 追加」ボタンに変更し、右上の「Add Link」と視覚的に差別化
  - 右上「Add Link」= グループ未選択でモーダルを開く（後からグループを選択）
  - グループ行「+ 追加」= そのグループを事前選択した状態でモーダルを開く
- **WebSocket 自動更新 ON/OFF トグル**: 「自動更新 ●」バッジをクリックで WebSocket を切断/再接続できるように対応
  - `wsEnabled` フラグで再接続ループを制御
  - OFF 時は「自動更新 OFF」（グレー）、再接続中は「再接続中...」（黄）を表示

### 技術的負債 記録

- `docs/issue7.md` を新規作成（**性能・同時アクセス・堅牢性 14件**）
  - HIGH 5件: WebSocket broadcast 競合、タイマー TOCTOU、在籍状態 N+1、FTP/SMB サーキットブレーカー不在、バックグラウンドタスク無音失敗
  - MEDIUM 5件: タスクリスト start 競合、ページネーション不在、DB 接続プール、ログイン時セッション競合、バッチ完了楽観ロック不在
  - LOW 4件: WS ハートビート不在、Excel メモリ使用、在籍状態非アクティブユーザー混入、暗号化失敗リスク

---

## 2026-02-27

### 勤怠履歴 月フィルタ UX 修正

- **問題**: 月フィルタ (`<input type="month">`) の値を変更しても、以前は別途 🔍 ボタンをクリックしないと履歴が再読み込みされなかった。ユーザーが検索ボタンを押し忘れると古いデータが表示されたまま残る問題があった
- **対応**:
  - `templates/attendance.html`: `filter-month` に `onchange="loadHistory()"` を追加（月変更で即時再読み込み）
  - 🔍 検索ボタンを 📅「今月に戻す」ボタン（`resetMonth()`）に置き換え（より直感的な操作）
  - `static/js/attendance.js`: `resetMonth()` 関数を追加（`filter-month` を当月にリセットして `loadHistory()` を実行）
  - スクリプトキャッシュバージョンを `?v=12` に更新

---

## 未実装・今後の予定

| 機能 | 状態 | 参照 |
|------|------|------|
| Wiki 添付ファイル API | DB・モデル実装済み、API・UI 未実装 | `docs/db-schema.md` セクション2.40 |
| Yjs リアルタイム共同編集 | 設計済み・未実装 | `docs/spec_wiki.md` セクション9.3 |
| portal_core ロール拡張 | 設計済み・未実装 | `docs/spec_roadmap.md` セクション4 |
| ログ検索 API | 実装済みCRUD・ルーター未接続 | `docs/spec_log_problem.md` |
| WebSocket broadcast 競合対策 | 技術的負債（HIGH） | `docs/issue7.md` セクション1-1 |
| タイマー TOCTOU 修正 | 技術的負債（HIGH） | `docs/issue7.md` セクション1-2 |
| FTP/SMB サーキットブレーカー | 技術的負債（HIGH） | `docs/issue7.md` セクション1-4 |
| バックグラウンドタスク自動復旧 | 技術的負債（HIGH） | `docs/issue7.md` セクション1-5 |
| ページネーション追加 | 技術的負債（MEDIUM） | `docs/issue7.md` セクション2-2 |
| タスク→日報のイベントバス化 | 技術的負債 | `docs/spec_common_separation.md` |
| 翻訳ファイルの portal_core 分離 | 技術的負債 | `docs/spec_common_separation.md` |
