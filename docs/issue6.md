# ISSUE-6: 実装状況・モジュール導入状況の監査

作成日: 2026-02-26

## 概要

アプリケーションの各機能について、外部モジュール（ライブラリ）を活用しているか、
独自実装（カスタム）かを機能別に整理する。
品質向上や保守コスト削減のためにモジュール化を検討すべき箇所を明記する。

---

## 1. 現在の依存パッケージ一覧

| パッケージ | バージョン | 用途 |
|-----------|-----------|------|
| fastapi | 0.115.6 | Web フレームワーク |
| starlette | 0.41.3 | FastAPI の基盤（ミドルウェア・WebSocket） |
| uvicorn | 0.34.0 | ASGI サーバー |
| sqlalchemy | 2.0.36 | ORM |
| alembic | 1.14.1 | DB マイグレーション |
| pydantic | 2.10.3 | バリデーション・スキーマ |
| email-validator | 2.1.0 | メールアドレス検証（Pydantic EmailStr） |
| passlib | 1.7.4 | パスワードハッシュ |
| bcrypt | 4.0.1 | bcrypt ハッシュアルゴリズム |
| itsdangerous | 2.2.0 | セッション署名（Starlette SessionMiddleware） |
| cryptography | 46.0.5 | Fernet 暗号化（FTP/SMB 認証情報） |
| httpx | 0.28.1 | HTTP クライアント（OAuth ユーザー情報取得） |
| httpx-oauth | 0.16.1 | OAuth2/PKCE フロー（認可URL構築・トークン交換） |
| babel | 2.18.0 | i18n（メッセージ抽出・翻訳） |
| openpyxl | 3.1.5 | Excel 出力（勤怠エクスポート） |
| smbprotocol | 1.16.0 | SMB/CIFS ファイルアクセス |
| ftputil | 5.1.0 | FTP 高レベルラッパー（MLSD/LIST フォールバック自動、os.path 互換 API） |
| python-dateutil | 2.9.0 | カレンダー繰り返しルール（rrule） |
| watchfiles | 1.1.1 | ホットリロード |
| websockets | 14.1 | WebSocket プロトコル（Starlette 経由） |

---

## 2. 機能別 実装状況

### 2-1. 認証・セッション管理

| コンポーネント | 方式 | 使用ライブラリ | 独自実装部分 | 評価 |
|--------------|------|----------------|------------|------|
| セッション管理 | Starlette SessionMiddleware + 署名 Cookie | `itsdangerous` | なし（ライブラリに委託） | ✅ 適切 |
| 認証ミドルウェア | カスタム | なし | `app_factory.py` 内の `auth_middleware()` | ✅ シンプルで十分 |
| セッション検証 | カスタム | なし | `portal_core/core/deps.py` — `session_version` チェック含む | ✅ 適切 |
| パスワードハッシュ | passlib bcrypt | `passlib[bcrypt]` | なし | ✅ 標準的 |

**ファイル:**
- `portal_core/portal_core/app_factory.py`（ミドルウェア）
- `portal_core/portal_core/core/deps.py`（DI）
- `portal_core/portal_core/core/security.py`（ハッシュ）

---

### 2-2. ログインレート制限・アカウントロックアウト

| コンポーネント | 方式 | 使用ライブラリ | 独自実装部分 | 評価 |
|--------------|------|----------------|------------|------|
| レート制限 | DB テーブル（`login_attempts`）ベース | なし | `portal_core/core/auth/rate_limiter.py`（72行） | ⚠️ 要検討 |
| アカウントロック | DB カラム（`users.locked_until`）ベース | なし | `rate_limiter.py` 内の `maybe_lock_account()` | ✅ 軽量で問題なし |

**代替モジュール候補:**
- **`slowapi`**: FastAPI 向けの [limits](https://pypi.org/project/limits/) ラッパー。デコレータで簡潔に記述可能。ただし Redis 等のストレージが必要なケースが多く、現在の DB ベース実装で十分ならそのままでよい。

**判定:** 現状の DB ベース実装はシンプルで外部ストレージ不要。**現状維持を推奨**。

---

### 2-3. パスワードポリシー

| コンポーネント | 方式 | 使用ライブラリ | 独自実装部分 | 評価 |
|--------------|------|----------------|------------|------|
| パスワード強度検証 | 正規表現 + stdlib `re` / `string` | なし（stdlib のみ） | `portal_core/core/auth/password_policy.py`（34行） | ⚠️ 要検討 |

**代替モジュール候補:**
- **`password-validator`** / **`zxcvbn`**: 辞書ベースの強度評価。現在の要件（文字種チェック）以上の「推測されやすいパスワード」検出が可能。
- **`pwdlib`** / **`password-strength`**: 設定可能な強度ポリシー。

**判定:** 現状の34行実装は要件を満たしており、テスト済み。モジュール化のメリットは「推測容易パスワード（password123 等）の拒否」が追加できる点のみ。現状維持または **`zxcvbn`** 導入を検討。

---

### 2-4. OAuth2 / SSO

> **2026-02-26 更新:** `httpx-oauth` 0.16.1 導入済み。`flow.py` を `BaseOAuth2` 使用に切り替え完了。

| コンポーネント | 方式 | 使用ライブラリ | 独自実装部分 | 評価 |
|--------------|------|----------------|------------|------|
| OAuth フロー（PKCE） | `BaseOAuth2`（httpx-oauth） | `httpx-oauth` | `core/auth/oauth/flow.py`（ファクトリ関数のみ） | ✅ ライブラリに委譲 |
| ユーザー情報取得 | `httpx.AsyncClient` 直接使用 | `httpx` | `flow.py` の `fetch_userinfo()`（動的 URL のため） | ✅ 適切 |
| Google プロバイダ | 独自ユーザー情報パーサー | なし | `core/auth/oauth/google.py` | ✅ パース処理のみ（フロー部分はライブラリ） |
| GitHub プロバイダ | 独自ユーザー情報パーサー | なし | `core/auth/oauth/github.py` | ✅ パース処理のみ（フロー部分はライブラリ） |
| CSRF State 生成 | `secrets` stdlib | なし | flow.py 内 `secrets.token_urlsafe()` | ✅ 適切 |
| PKCE 生成 | `hashlib` + `base64` stdlib | なし | flow.py 内カスタム実装（ライブラリ非使用・標準で十分） | ✅ 適切 |

**設計メモ:**
- DB の `OAuthProvider` モデルでプロバイダ設定を動的管理しているため、`GoogleOAuth2`/`GitHubOAuth2` ではなく `BaseOAuth2` を on-the-fly で生成する方式を採用。
- OAuth エンドポイントがすべて同期 `def` のため、`asyncio.run()` を sync-to-async ブリッジとして使用。
- `oauth_service.py` / `api_oauth.py` / テストのモックパスは変更なし。

---

### 2-5. パスワードリセット

| コンポーネント | 方式 | 使用ライブラリ | 独自実装部分 | 評価 |
|--------------|------|----------------|------------|------|
| トークン生成 | `secrets.token_urlsafe(32)` | なし（stdlib） | `password_reset_service.py` | ✅ 適切 |
| トークン保存 | SHA-256 ハッシュ（DB 保存） | なし（`hashlib` stdlib） | 同上 | ✅ セキュア |
| 有効期限管理 | DB カラム（`expires_at`）| なし | 同上 | ✅ 適切 |
| メール送信 | smtplib（stdlib） | なし | `email_service.py` | ⚠️ 要検討 |

---

### 2-6. メール送信

| コンポーネント | 方式 | 使用ライブラリ | 独自実装部分 | 評価 |
|--------------|------|----------------|------------|------|
| SMTP 送信 | 同期 smtplib | なし（stdlib） | `portal_core/services/email_service.py`（55行） | ⚠️ 要検討 |
| HTML/テキスト本文 | `email.mime` stdlib | なし | 同上 | ✅ 十分 |

**代替モジュール候補:**
- **`fastapi-mail`**: FastAPI 向け非同期メール送信ライブラリ。`aiosmtplib` ベース、テンプレート対応。現状の smtplib は同期処理のため、メール送信中にリクエストがブロックされる可能性がある。
- **`aiosmtplib`**: 非同期 SMTP クライアント。メール送信を `asyncio` でノンブロッキングに実行可能。

**判定:** 現在はパスワードリセットメールのみ。ユーザー数が増えるかメール送信頻度が高まるなら **`fastapi-mail`** への移行を推奨。現状の規模では現状維持でも可。

---

### 2-7. バックグラウンドタスク・スケジューリング

| コンポーネント | 方式 | 使用ライブラリ | 独自実装部分 | 評価 |
|--------------|------|----------------|------------|------|
| ログスキャナー | `asyncio.create_task()` + ポーリング | なし（asyncio stdlib） | `app/services/log_scanner.py`（99行） | ⚠️ 要検討 |
| サイトヘルスチェッカー | `asyncio.gather()` + ポーリング | なし（asyncio stdlib） | `app/services/site_checker.py` | ⚠️ 要検討 |
| カレンダーリマインダー | 同上 | なし | `app/services/reminder_checker.py` | ⚠️ 要検討 |
| タスク管理 | FastAPI lifespan + `app.state` | なし | `app_factory.py` lifespan | ✅ 適切 |

**代替モジュール候補:**
- **`APScheduler`**: cron 式・interval 指定のジョブスケジューリング。各バックグラウンドタスクの `while True: sleep()` ループを宣言的に置き換えられる。エラーハンドリング・ジョブ管理 UI も内包。
- **`rq` + Redis**: ジョブキュー。メール送信等の非同期ジョブに適する。ただし Redis が必要。
- **Celery**: 本格的な分散タスクキュー。現在の規模には過剰。

**判定:** 現状の `asyncio` ポーリング実装は動作しているが、エラー後のリトライ・ジョブの可視化・停止操作が困難。ジョブの種類が増えた場合は **`APScheduler`** の導入を検討。

---

### 2-8. 認証情報暗号化（FTP/SMB パスワード）

| コンポーネント | 方式 | 使用ライブラリ | 独自実装部分 | 評価 |
|--------------|------|----------------|------------|------|
| Fernet 暗号化 | `cryptography.fernet.Fernet` | `cryptography` | `portal_core/core/encryption.py`（50行） | ✅ 適切 |
| 鍵管理 | `.env` の `CREDENTIAL_ENCRYPTION_KEY` | なし | 設定ファイルベース | ✅ 十分 |

---

### 2-9. バリデーション

| コンポーネント | 方式 | 使用ライブラリ | 独自実装部分 | 評価 |
|--------------|------|----------------|------------|------|
| リクエスト/レスポンス | Pydantic 2.10 | `pydantic` + `email-validator` | スキーマ定義のみ | ✅ 標準的 |
| カスタムバリデーター | `@field_validator` | Pydantic | 各スキーマの業務ルール | ✅ 適切 |

---

### 2-10. データベース・マイグレーション

| コンポーネント | 方式 | 使用ライブラリ | 独自実装部分 | 評価 |
|--------------|------|----------------|------------|------|
| ORM | SQLAlchemy 2.0 | `sqlalchemy` | モデル定義・CRUD | ✅ 標準的 |
| マイグレーション | Alembic | `alembic` | マイグレーションスクリプト | ✅ 標準的 |
| 接続管理 | `SessionLocal` ジェネレータ | SQLAlchemy | `database.py`（12行） | ✅ 適切 |
| 全文検索 | PostgreSQL TSVECTOR + GIN | PostgreSQL ネイティブ | `wiki_page.py` のカラム定義 | ✅ 適切 |

---

### 2-11. WebSocket

| コンポーネント | 方式 | 使用ライブラリ | 独自実装部分 | 評価 |
|--------------|------|----------------|------------|------|
| WebSocket プロトコル | Starlette 内蔵（websockets ライブラリ経由） | `starlette` / `websockets` | なし | ✅ 適切 |
| 接続管理 | カスタム `WebSocketManager` | なし | `websocket_manager.py`（32行） | ✅ シンプルで十分 |
| ブロードキャスト | ループ + エラー検出 | なし | 同上 | ✅ 現規模に適切 |

**代替モジュール候補:**
- **`broadcaster`**: Redis Pub/Sub や PostgreSQL LISTEN/NOTIFY をバックエンドにした WebSocket ブロードキャスト。複数プロセス・サーバーへのスケールが可能。

**判定:** 現在は単一プロセス稼働のため現状維持で問題なし。マルチプロセス・ロードバランサー構成になれば **`broadcaster`** + Redis の導入を検討。

---

### 2-12. 国際化（i18n）

| コンポーネント | 方式 | 使用ライブラリ | 独自実装部分 | 評価 |
|--------------|------|----------------|------------|------|
| バックエンド翻訳 | gettext + Babel | `babel`, Python `gettext` stdlib | `portal_core/core/i18n.py`（40行） | ✅ 標準的 |
| テンプレート翻訳 | Jinja2 `_()` / `{% trans %}` | Jinja2 | なし | ✅ 適切 |
| フロントエンド翻訳 | JSON ファイル + 独自 `i18n.t()` | なし | `static/js/common.js` の `i18n` オブジェクト | ⚠️ 要検討 |

**代替モジュール候補（フロントエンド）:**
- **`i18next`**: JavaScript i18n の標準。フォールバック・複数形対応・プラグイン充実。
- **`Lingui`**: React 等のコンポーネント向けだが vanilla JS でも使用可。

**判定:** フロントエンドの独自 `i18n.t()` は基本的な置換のみ対応。複数形（"1 件" / "2 件以上"）の対応が必要になれば **`i18next`** への移行を検討。現状規模では現状維持で可。

---

### 2-13. CSRF 対策

> **2026-02-27 更新:** `fastapi-csrf-protect` 1.0.7 導入済み。TD-04 解消。

| コンポーネント | 方式 | 使用ライブラリ | 独自実装部分 | 評価 |
|--------------|------|----------------|------------|------|
| CSRF チェック | Double Submit Cookie パターン | `fastapi-csrf-protect` 1.0.7 | `app_factory.py` のミドルウェア + `_render()` でトークン生成 | ✅ 標準的 |

**実装状況:**
- サーバーが `csrf_token`（平文）+ `signed_token`（署名済み）を生成
- `signed_token` を HttpOnly Cookie に保存（cookie 名: `fastapi-csrf-token`）
- クライアントは `X-CSRFToken: {csrf_token}` ヘッダーを送信（`api.js` のラッパーが自動付与）
- サーバーは Cookie 内の `signed_token` と `X-CSRFToken` を照合
- 除外: `POST /api/logs/`（外部システム）、`/api/auth/`（ログイン等）

**判定:** ✅ **導入済み** — `fastapi-csrf-protect` による Double Submit Cookie で十分な CSRF 保護を実現。

---

### 2-14. Excel エクスポート

| コンポーネント | 方式 | 使用ライブラリ | 独自実装部分 | 評価 |
|--------------|------|----------------|------------|------|
| Excel 生成 | openpyxl | `openpyxl` | `attendance_service.py` のフォーマット処理（100行） | ✅ 適切 |

---

### 2-15. カレンダー繰り返しルール

| コンポーネント | 方式 | 使用ライブラリ | 独自実装部分 | 評価 |
|--------------|------|----------------|------------|------|
| rrule パース・展開 | python-dateutil の `rrulestr` | `python-dateutil` | `calendar_service.py` のイベント展開ロジック | ✅ 適切 |
| iCalendar フォーマット | RFC 5545 準拠文字列（`FREQ=WEEKLY` 等） | dateutil のみ | なし | ✅ 適切 |

---

### 2-16. FTP / SMB ファイルアクセス

> **2026-02-26 更新:** `ftputil` 5.1.0 導入済み。`FTPConnector` を ftputil ベースに置換完了。

| コンポーネント | 方式 | 使用ライブラリ | 独自実装部分 | 評価 |
|--------------|------|----------------|------------|------|
| FTP 接続 | ftputil（ftplib 高レベルラッパー） | `ftputil` | `remote_connector.py` の `FTPConnector`（約70行） | ✅ ライブラリに委譲 |
| SMB/CIFS 接続 | smbprotocol | `smbprotocol` | `SMBConnector`（100行） | ✅ 適切 |
| 接続抽象化 | 独自 ABC | なし | `RemoteConnector` 抽象基底クラス | ✅ 設計良好 |
| ファイルパターン照合 | fnmatch stdlib | なし | 1行 | ✅ 十分 |

**設計メモ:**
- port・passive mode・timeout を ftputil に渡すため `_make_ftp_session_class()` ファクトリを使用。
- MLSD → LIST フォールバック（旧70行の手動実装）はライブラリ内部で自動処理。
- `SMBConnector`・`create_connector()`・サービス層・テストは無変更（`create_connector` レベルのモックも継続動作）。

---

### 2-17. 監査ログ（認証イベント）

| コンポーネント | 方式 | 使用ライブラリ | 独自実装部分 | 評価 |
|--------------|------|----------------|------------|------|
| 認証イベント記録 | DB テーブル（`auth_audit_logs`） | なし | `core/auth/audit.py`（35行） | ✅ シンプルで十分 |

---

## 3. 対応優先度まとめ

| 優先度 | 機能 | 現状の課題 | 推奨アクション |
|--------|------|-----------|---------------|
| ✅ 完了 | OAuth2 | ~~新プロバイダ追加のたびに独自実装が必要~~ | **`httpx-oauth`** 0.16.1 導入済み（2026-02-26） |
| ✅ 完了 | FTP アクセス | ~~MLSD/LIST フォールバックの手動実装が複雑~~ | **`ftputil`** 5.1.0 導入済み（2026-02-26） |
| ✅ 完了 | CSRF 対策 | ~~Origin/Referer のみでは限定的~~ | **`fastapi-csrf-protect`** 1.0.7 導入済み（2026-02-27） |
| ✅ 完了 | メール送信 | ~~smtplib は同期処理（送信中ブロック）~~ | `BackgroundTasks.add_task()` によるバックグラウンド実行に変更（2026-02-27） |
| 🟡 中 | バックグラウンドタスク | ジョブ可視化・リトライが困難 | ジョブ増加時に **`APScheduler`** 導入 |
| 🟡 中 | パスワードポリシー | 辞書攻撃耐性の検証がない | 必要なら **`zxcvbn`** 追加 |
| 🟢 低 | フロントエンド i18n | 複数形対応なし | 必要なら **`i18next`** へ移行 |
| 🟢 低 | レート制限 | DB ベースは十分（Redis 不要） | 現状維持 |
| 🟢 低 | WebSocket 管理 | 単一プロセス前提 | 複数プロセス化時に **`broadcaster`** 検討 |
| ✅ 不要 | パスワードハッシュ | passlib + bcrypt で適切 | 変更不要 |
| ✅ 不要 | バリデーション | Pydantic 2 で適切 | 変更不要 |
| ✅ 不要 | DB/マイグレーション | SQLAlchemy + Alembic で適切 | 変更不要 |
| ✅ 不要 | 暗号化 | cryptography Fernet で適切 | 変更不要 |
| ✅ 不要 | Excel 出力 | openpyxl で適切 | 変更不要 |
| ✅ 不要 | カレンダー rrule | python-dateutil で適切 | 変更不要 |
| ✅ 不要 | 全文検索 | PostgreSQL TSVECTOR で十分 | 変更不要 |

---

## 4. 技術的負債として記録すべき事項

### TD-01: OAuth2 の独自実装 ✅ **解消済み（2026-02-26）**
- **場所:** `portal_core/portal_core/core/auth/oauth/flow.py`
- ~~**問題:** 新プロバイダ（Microsoft Entra、Slack 等）追加時に各社 API 仕様に合わせた独自コード追加が必要~~
- **対応:** `httpx-oauth` 0.16.1 を導入。`BaseOAuth2` に認可URL構築・トークン交換を委譲。
- **残存:** ユーザー情報パーサー（`google.py`, `github.py`）は各プロバイダの JSON 形式差異のため独自実装を維持（正当な設計）

### TD-02: メール送信の同期処理 ✅ **解消済み（2026-02-27）**
- **場所:** `portal_core/portal_core/services/email_service.py`, `portal_core/portal_core/routers/api_auth.py`
- ~~**問題:** smtplib は同期処理であり、SMTP サーバーの遅延がリクエストスレッドをブロックする~~
- **対応:** `request_password_reset()` に `add_background_task` パラメータを追加。`forgot_password` ルーターが `background_tasks.add_task` を渡すことで、メール送信が FastAPI の `BackgroundTasks` メカニズムによりレスポンス返却後に非同期実行される。`add_background_task=None` のときは従来通り同期実行（テスト・CLI用途の後方互換性を維持）。

### TD-03: バックグラウンドタスクの可視性
- **場所:** `app/services/log_scanner.py`, `site_checker.py`, `reminder_checker.py`
- **問題:** ジョブの実行状況・エラー履歴・手動再実行の手段がない。`app.state` に保持したタスクが無言で失敗する可能性がある
- **対策:** ジョブごとのステータス記録 or `APScheduler` 導入

### TD-04: CSRF 対策の方式 ✅ **解消済み（2026-02-27）**
- **場所:** `portal_core/portal_core/app_factory.py`
- ~~**問題:** Origin/Referer ヘッダーの検証のみであり、リバースプロキシ構成や一部クライアントで Referer が送信されない場合に保護が効かない可能性~~
- **対応:** `fastapi-csrf-protect` 1.0.7 を導入。Double Submit Cookie パターンを実装。`X-CSRFToken` ヘッダーをすべての POST/PUT/PATCH/DELETE で必須化（`/api/auth/`, `/api/logs/` は除外）。

### TD-05: フロントエンド i18n の複数形未対応
- **場所:** `static/js/common.js` の `i18n.t()`
- **問題:** "1 件の結果" / "N 件の結果" のような複数形切替に非対応（現在は `{count} 件` の文字列置換のみ）
- **対策:** 必要なら `i18next` に移行
