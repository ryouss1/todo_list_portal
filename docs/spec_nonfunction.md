# 非機能要件・テスト仕様

> 本ドキュメントは [spec.md](./spec.md) の補足資料です。

---

## 1. ロギング

### 1.1 アプリケーションログ

| 設定項目 | 値 |
|---------|-----|
| 出力ファイル | `app.log` |
| 最大ファイルサイズ | 10MB（10,485,760 bytes） |
| ローテーション数 | 最大5ファイル |
| エンコーディング | UTF-8 |
| コンソール出力 | あり（stdout） |
| ログレベル | INFO |

### 1.2 ログフォーマット

```
%(asctime)s [%(levelname)s] %(name)s: %(message)s
```

日時フォーマット: `%Y-%m-%d %H:%M:%S`

### 1.3 ロガー構成

| ロガー名 | レベル | ハンドラ |
|---------|--------|---------|
| `app` | INFO | console, file |
| root | INFO | console, file |

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
| CSRF対策 | `csrf_middleware` で Origin/Referer ヘッダを検証（state-changing methods） |
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
| エンドポイント | `/ws/logs`, `/ws/presence`, `/ws/alerts` |
| プロトコル | ws:// / wss:// |
| 接続管理 | WebSocketManagerによるアクティブ接続リスト管理 |
| デッド接続の除去 | ブロードキャスト時に送信失敗した接続を自動除去 |
| クライアント側再接続 | 切断後3秒で自動再接続 |
| クライアント側バッファ | 最大200件のログを保持 |

---

## 6. テスト仕様

### 6.1 テスト構成

| 項目 | 内容 |
|------|------|
| テストフレームワーク | pytest |
| テストクライアント | FastAPI TestClient |
| データ分離方式 | テストごとにトランザクションを開始し、テスト後にロールバック |
| テスト用DB | 本番と同じDBを使用（トランザクションロールバックにより既存データに影響なし） |
| テスト設定ファイル | `tests/conftest.py` |

### 6.2 テストカバレッジ

| テストファイル | 対象 | テストケース数 |
|---------------|------|--------------|
| `tests/test_auth.py` | Auth API + ミドルウェア | 12件 |
| `tests/test_auth_security.py` | 認証セキュリティ（パスワードポリシー + レート制限 + ロックアウト + セッション無効化 + 監査ログ） | 27件 |
| `tests/test_oauth.py` | OAuth2/SSO（プロバイダ管理 + フロー + リンク） | 22件 |
| `tests/test_password_reset.py` | パスワードリセット（トークン生成 + 検証 + リセット + レート制限 + ページ） | 23件 |
| `tests/test_authorization.py` | データ所有者分離（Todo visibility含む） | 14件 |
| `tests/test_users.py` | User API（CRUD + RBAC + 自己編集 + パスワード） | 28件 |
| `tests/test_todos.py` | Todo API（visibility含む） | 17件 |
| `tests/test_attendances.py` | Attendance API（breaks + presets + input_type + 手動入力 + 月別フィルタ） | 62件 |
| `tests/test_tasks.py` | Task API（タイマー + done + batch-done + category） | 33件 |
| `tests/test_task_list.py` | Task List API（assignment + start + time蓄積 + status同期 + フィルタ） | 39件 |
| `tests/test_task_categories.py` | Task Category API（RBAC含む） | 11件 |
| `tests/test_reports.py` | Report API + 認可（category + time_minutes + backlog_ticket_id） | 20件 |
| `tests/test_summary.py` | Summary API（category trends + daily） | 15件 |
| `tests/test_presence.py` | Presence API（Backlogチケット含む） | 15件 |
| `tests/test_logs.py` | Log API | 7件 |
| `tests/test_log_sources.py` | Log Source API（CRUD + 複数パス + 認証情報マスク + バリデーション + RBAC + 接続テスト + ファイル一覧 + スキャン + アラート連携 + フォルダリンク + コンテンツ読み込み + 再読込） | 100件 |
| `tests/test_log_scanner.py` | バックグラウンドスキャナー（start/stop + ポーリング判定 + エラー隔離 + WebSocketブロードキャスト） | 11件 |
| `tests/test_alerts.py` | Alert API（severity検証 + RBAC + フィルタページ） | 17件 |
| `tests/test_alert_rules.py` | Alert Rule API + 評価エンジン（条件検証 + RBAC） | 29件 |
| `tests/test_calendar.py` | Calendar API（イベント CRUD + 繰り返し + 参加者） | 29件 |
| `tests/test_calendar_rooms.py` | Calendar Room API（CRUD + 空き状況） | 18件 |
| `tests/test_groups.py` | Group API（CRUD + RBAC） | 11件 |
| `tests/test_websocket.py` | WebSocket（認証含む） | 4件 |
| `tests/test_i18n.py` | 国際化（ロケール切替 + 翻訳 + エラーメッセージ） | 17件 |
| **合計** | | **581件** |

各テストケースの詳細は `tests/` ディレクトリ内のテストファイルを直接参照してください。
