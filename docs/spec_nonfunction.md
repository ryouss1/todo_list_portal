# 非機能要件・テスト仕様

> 本ドキュメントは [spec.md](./spec.md) の補足資料です。

---

## 1. ロギング

### 1.1 ログファイル構成

ログは `logs/` ディレクトリ配下の3ファイルに分離される。`logs/` ディレクトリは起動時に自動生成。

| ファイル | 対象ロガー | レベル | ローテーション |
|---------|-----------|--------|--------------|
| `logs/app.log` | アプリ全般（SQL除く） | INFO + | 10MB × 5 |
| `logs/sql.log` | SQLAlchemy クエリ・接続プール | DEBUG +（デフォルト） | 10MB × 5 |
| `logs/error.log` | 全ロガーのエラー | ERROR + | 10MB × 5 |

- `logs/` は `.gitignore` 登録済み（Git 管理外）
- コンソール（stdout）にも INFO+ を出力

### 1.2 ログフォーマット

```
%(asctime)s [%(levelname)s] %(name)s: %(message)s
```

日時フォーマット: `%Y-%m-%d %H:%M:%S`

### 1.3 ロガー構成

| ロガー名 | レベル | ハンドラ | propagate |
|---------|--------|---------|-----------|
| `app` | INFO | console, app_file, error_file | False |
| `portal_core` | INFO | console, app_file, error_file | False |
| `sqlalchemy.engine` | SQL_LOG_LEVEL | sql_file のみ | False |
| `sqlalchemy.pool` | SQL_LOG_LEVEL | sql_file のみ | False |
| root | INFO | console, app_file, error_file | — |

### 1.4 環境変数

| 変数名 | デフォルト | 説明 |
|--------|-----------|------|
| `LOG_LEVEL` | `INFO` | アプリ全般ログレベル |
| `LOG_DIR` | `logs` | ログ出力ディレクトリパス |
| `SQL_LOG_LEVEL` | `DEBUG` | SQLAlchemy ログレベル（本番環境では `WARNING` 推奨） |
| `LOG_MAX_BYTES` | `10485760` | ローテーションサイズ（バイト） |
| `LOG_BACKUP_COUNT` | `5` | 保持するローテーションファイル数 |

> **注意**: `SQL_LOG_LEVEL=DEBUG` はバインドパラメータ値（パスワード等）を含む場合があるため、本番環境では `.env` で `SQL_LOG_LEVEL=WARNING` を設定すること。

---

## 2. データベース接続

| 設定項目 | 値 |
|---------|-----|
| ORM | SQLAlchemy 2.0.36 |
| ドライバ | psycopg2-binary 2.9.10 |
| 接続プール | SQLAlchemy デフォルト |
| pool_pre_ping | 有効（接続ヘルスチェック） |
| セッション管理 | リクエストごとに生成・クローズ（`get_db` ジェネレータ） |
| autocommit | 無効 |
| autoflush | 無効 |

---

## 3. セキュリティ

### 3.1 実装済み

| 対策 | 実装方法 |
|------|---------|
| 認証 | セッションベース認証（`SessionMiddleware` + 署名Cookie） |
| パスワード保護 | bcryptハッシュ（`passlib[bcrypt]`） |
| アクセス制御 | 認証ミドルウェア（ページ→リダイレクト、API→401） |
| 認可（RBAC） | `users.role` カラム（admin/user）、`require_admin` 依存性注入 |
| CSRF対策 | `fastapi-csrf-protect` による Double Submit Cookie パターン（`X-CSRF-Token` ヘッダー必須、除外: `/api/auth/`, `/api/logs/`）。JS 層は `api.js` ラッパー（`api.post/put/del` 等）経由でヘッダー自動付与。`wiki.js` も同ラッパーに統一済み |
| XSS対策 | フロントエンドのJavaScriptでHTMLエスケープを実施（`escapeHtml`関数） |
| 入力バリデーション | PydanticスキーマによるAPIリクエストの型・必須チェック |
| SQLインジェクション対策 | SQLAlchemy ORMの使用によるパラメータバインド |
| セッション改ざん防止 | `itsdangerous`による署名付きCookie |
| WebSocket認証 | Cookie セッション認証、未認証時は 4401 で切断 |
| メールアドレス検証 | Pydantic `EmailStr` による入力バリデーション（`email-validator`） |
| パスワードポリシー | `password_policy.py` — 最小/最大文字数、大文字/小文字/数字/特殊文字要件（設定可能） |
| ログインレート制限 | `rate_limiter.py` — 15分間に5回失敗でブロック（設定可能） |
| アカウントロックアウト | `users.locked_until` — 失敗回数超過で30分ロック、管理者アンロック可 |
| セッション無効化 | `users.session_version` — パスワード変更/ロール変更時にセッション強制失効 |
| 認証監査ログ | `auth_audit_logs` テーブル — ログイン成功/失敗、パスワード変更等の記録 |
| OAuth2/SSO | Authorization Code + PKCE フロー、Google/GitHub対応、メール自動リンク |
| 認証情報暗号化 | Fernet (AES-128-CBC + HMAC-SHA256) による FTP/SMB 接続情報の暗号化保存（`cryptography`） |

### 3.2 未実装

| 項目 | 備考 |
|------|------|
| HTTPS | アプリケーション層では未対応（リバースプロキシで対応可） |

---

## 4. 起動設定

| 設定項目 | デフォルト値 |
|---------|-------------|
| ホスト | `0.0.0.0`（全インターフェース） |
| ポート | `8000` |
| ホットリロード | 有効（開発モード） |
| ASGIサーバー | Uvicorn 0.34.0 |

---

## 5. WebSocket

| 設定項目 | 値 |
|---------|-----|
| エンドポイント | `/ws/logs`, `/ws/presence`, `/ws/alerts`, `/ws/sites` |
| プロトコル | ws:// / wss:// |
| 接続管理 | WebSocketManagerによるアクティブ接続リスト管理 |
| デッド接続の除去 | ブロードキャスト時に送信失敗した接続を自動除去 |
| クライアント側再接続 | 切断後3秒で自動再接続 |
| クライアント側バッファ | 最大200件のログを保持 |
| ハートビート (ping) | `WS_PING_INTERVAL` 秒間メッセージがなければ ping を送信（デフォルト: 30秒） |
| ハートビートタイムアウト | `WS_PING_TIMEOUT` 秒以内に pong がなければゾンビ接続と判定して切断（デフォルト: 10秒） |

**WebSocket 関連環境変数:**

| 変数名 | デフォルト | 説明 |
|--------|-----------|------|
| `WS_PING_INTERVAL` | `30` | アイドル状態で ping を送信するまでの秒数 |
| `WS_PING_TIMEOUT` | `10` | ping 応答（pong）を待つタイムアウト秒数。超過でゾンビ接続と判定し切断 |

---

## 6. テスト仕様

### 6.1 テスト構成

| 項目 | 内容 |
|------|------|
| テストフレームワーク | pytest |
| テストクライアント | FastAPI TestClient |
| データ分離方式 | テストごとにトランザクションを開始し、テスト後にロールバック |
| テスト用DB | 本番と同じDBを使用（トランザクションロールバックにより既存データに影響なし） |
| コアテスト設定ファイル | `portal_core/tests/conftest.py`（`core_app` フィクスチャ使用、独立実行可） |
| アプリテスト設定ファイル | `tests/conftest.py`（`from main import app` 使用） |

### 6.2 テストカバレッジ

#### portal_core テスト（`portal_core/tests/`）

portal_core 単体で実行可能。`core_app` フィクスチャ（PortalApp 単体ビルド）を使用。

| テストファイル | 対象 | テストケース数 |
|---------------|------|--------------|
| `portal_core/tests/test_auth.py` | Auth API + ミドルウェア + セッション一括更新（issue7 2-4） | 11件 |
| `portal_core/tests/test_auth_security.py` | 認証セキュリティ（パスワードポリシー + レート制限 + ロックアウト + セッション無効化 + 監査ログ） | 27件 |
| `portal_core/tests/test_oauth.py` | OAuth2/SSO（プロバイダ管理 + フロー + リンク） | 22件 |
| `portal_core/tests/test_password_reset.py` | パスワードリセット（トークン生成 + 検証 + リセット + レート制限 + ページ） | 23件 |
| `portal_core/tests/test_users.py` | User API（CRUD + RBAC + 自己編集 + パスワード） | 28件 |
| `portal_core/tests/test_departments.py` | Department API（CRUD + RBAC + ユーザー所属） | 32件 |
| `portal_core/tests/test_websocket.py` | WebSocket（認証 + 並行ブロードキャスト競合 + ハートビート ping/pong + ゾンビ接続検出） | 9件 |
| `portal_core/tests/test_i18n.py` | 国際化（ロケール切替 + 翻訳 + エラーメッセージ） | 13件 |
| `portal_core/tests/test_crud_base.py` | CRUDBase ジェネリッククラス（Group モデル使用 + get_db ロールバック検証） | 14件 |
| **コア小計** | | **179件** |

#### アプリテスト（`tests/`）

`from main import app`（フルアプリ）を使用。

| テストファイル | 対象 | テストケース数 |
|---------------|------|--------------|
| `tests/test_authorization.py` | データ所有者分離（Todo visibility含む） | 14件 |
| `tests/test_todos.py` | Todo API（visibility含む） | 17件 |
| `tests/test_attendances.py` | Attendance API（breaks + presets + input_type + 手動入力 + 月別フィルタ + 前日未退勤検出） | 70件 |
| `tests/test_tasks.py` | Task API（タイマー + done + batch-done + category + TOCTOU/ロストアップデート保護 + batch-done SELECT FOR UPDATE） | 39件 |
| `tests/test_task_list.py` | Task List API（assignment + start + time蓄積 + status同期 + フィルタ + ページネーション） | 48件 |
| `tests/test_task_categories.py` | Task Category API（RBAC含む） | 11件 |
| `tests/test_reports.py` | Report API + 認可（category + time_minutes + backlog_ticket_id） | 20件 |
| `tests/test_summary.py` | Summary API（category trends + daily） | 15件 |
| `tests/test_presence.py` | Presence API（Backlogチケット + アクティブタスク上限 + 非アクティブユーザー除外） | 19件 |
| `tests/test_logs.py` | Log API | 7件 |
| `tests/test_log_sources.py` | Log Source API（CRUD + 複数パス + 認証情報マスク + バリデーション + RBAC + 接続テスト + ファイル一覧 + スキャン + アラート連携 + フォルダリンク + コンテンツ読み込み + 再読込 + サーキットブレーカー） | 105件 |
| `tests/test_log_scanner.py` | バックグラウンドスキャナー（start/stop + ポーリング判定 + エラー隔離 + WebSocketブロードキャスト + ウォッチドッグ） | 14件 |
| `tests/test_alerts.py` | Alert API（severity検証 + RBAC + フィルタページ） | 17件 |
| `tests/test_alert_rules.py` | Alert Rule API + 評価エンジン（条件検証 + RBAC） | 30件 |
| `tests/test_calendar.py` | Calendar API（イベント CRUD + 繰り返し + 参加者） | 29件 |
| `tests/test_calendar_rooms.py` | Calendar Room API（CRUD + 空き状況） | 18件 |
| `tests/test_crud_base.py` | CRUDBase ジェネリッククラス（TaskCategory モデル使用） | 13件 |
| `tests/test_site_links.py` | Site Links API（CRUD + owner認可 + URL保護 + ヘルスチェック + バックグラウンドチェッカー + ページ） | 45件 |
| `tests/test_wiki.py` | Wiki API（カテゴリ + タグ + ページCRUD + 階層 + タグフィルタ + ページ移動 + タスクリンク + ルート + visibility + ページネーション） | 53件 |
| **アプリ小計** | | **584件** |

| | テスト数 |
|------|---------|
| **全合計** | **763件** |

```bash
# portal_core 単体テスト（179件）
cd portal_core && pytest tests/ -q

# アプリテスト（584件）
pytest tests/ -q

# 全テスト（CI用）
cd portal_core && pytest tests/ -q && cd .. && pytest tests/ -q
```

各テストケースの詳細は各ディレクトリ内のテストファイルを直接参照してください。
