# 認証セキュリティ強化 設計書

## 概要

認証機能のセキュリティを強化するため、以下の機能を実装した。

- パスワードポリシー（強度検証）
- ログインレート制限
- アカウントロックアウト
- セッション無効化
- 認証監査ログ

---

## 1. パスワードポリシー

### 設定項目

| 環境変数 | デフォルト | 説明 |
|---------|-----------|------|
| `PASSWORD_MIN_LENGTH` | 8 | 最小文字数 |
| `PASSWORD_MAX_LENGTH` | 128 | 最大文字数 |
| `PASSWORD_REQUIRE_UPPERCASE` | true | 大文字必須 |
| `PASSWORD_REQUIRE_LOWERCASE` | true | 小文字必須 |
| `PASSWORD_REQUIRE_DIGIT` | true | 数字必須 |
| `PASSWORD_REQUIRE_SPECIAL` | false | 特殊文字必須 |

### 実装

- ファイル: `app/core/auth/password_policy.py`
- 関数: `validate_password(password: str) -> None`
- 違反時に `ConflictError` を raise（全違反をセミコロン区切りで返却）
- 統合箇所: `user_service.create_user()`, `user_service.change_password()`, `user_service.reset_password()`

---

## 2. ログインレート制限

### 設定項目

| 環境変数 | デフォルト | 説明 |
|---------|-----------|------|
| `LOGIN_MAX_ATTEMPTS` | 5 | ウィンドウ内の最大失敗回数 |
| `LOGIN_RATE_LIMIT_WINDOW_MINUTES` | 15 | 判定ウィンドウ（分） |

### 実装

- ファイル: `app/core/auth/rate_limiter.py`
- `check_rate_limit(db, email)` — 失敗回数がしきい値を超えたら `ConflictError` を raise
- `record_attempt(db, email, success, ip_address)` — ログイン試行を `login_attempts` テーブルに記録
- `cleanup_old_attempts(db, days=90)` — 古い記録の定期削除

### データベース

- テーブル: `login_attempts`（email, ip_address, success, attempted_at）

---

## 3. アカウントロックアウト

### 設定項目

| 環境変数 | デフォルト | 説明 |
|---------|-----------|------|
| `ACCOUNT_LOCKOUT_MINUTES` | 30 | ロックアウト期間（分） |

### 実装

- `check_account_locked(db, user)` — `users.locked_until` が未来の場合に `AuthenticationError` を raise
- `maybe_lock_account(db, user) -> bool` — 失敗回数がしきい値に達したら `locked_until` を設定
- `unlock_account(db, user)` — `locked_until = None` に設定

### 管理者アンロック

- API: `POST /api/users/{id}/unlock`（admin only）
- サービス: `user_service.unlock_user(db, user_id)`

### 認証フロー

```
authenticate(db, email, password, ip_address, user_agent):
  1. check_rate_limit(db, email)          — レート制限チェック
  2. ユーザー検索
  3. check_account_locked(db, user)       — ロック状態チェック
  4. パスワード検証
  5. 失敗時: record_attempt(success=False) + maybe_lock_account()
  6. is_active チェック
  7. 成功時: record_attempt(success=True)
```

---

## 4. セッション無効化

### 設計

Starlette の `SessionMiddleware` はクライアントサイドセッション（署名Cookie）のため、サーバー側でセッションを列挙・無効化できない。`session_version` カラム方式で解決。

### 実装

- `users.session_version` カラム（Integer, NOT NULL, DEFAULT 1）
- ログイン時: `session["session_version"] = user.session_version` を設定
- リクエスト時: `get_current_user_id()` で DB の `session_version` と照合
- 不一致時: セッションをクリアし `AuthenticationError` を raise

### インクリメント契機

| 契機 | 場所 |
|------|------|
| パスワード変更 | `user_service.change_password()` |
| パスワードリセット | `user_service.reset_password()` |
| ロール変更 | `user_service.update_user()` |
| アカウント無効化 | `user_service.update_user()` |

---

## 5. 認証監査ログ

### 実装

- ファイル: `app/core/auth/audit.py`
- 関数: `log_auth_event(db, event_type, user_id, email, ip_address, user_agent, details)`
- CRUD: `app/crud/auth_audit_log.py`

### イベント種別

| event_type | 説明 | 記録箇所 |
|------------|------|---------|
| `login_success` | ログイン成功 | `auth_service.authenticate()` |
| `login_failure` | ログイン失敗 | `auth_service.authenticate()` |
| `logout` | ログアウト | `api_auth.py` |
| `password_change` | パスワード変更 | `user_service.change_password()` |
| `password_reset` | パスワードリセット | `user_service.reset_password()` |
| `account_locked` | アカウントロック | `rate_limiter.maybe_lock_account()` |
| `account_unlocked` | アカウントアンロック | `user_service.unlock_user()` |
| `role_changed` | ロール変更 | `user_service.update_user()` |
| `session_invalidated` | セッション無効化 | `user_service._increment_session_version()` |
| `oauth_login` | OAuthログイン | `oauth_service.handle_callback()` |
| `oauth_link` | OAuthアカウントリンク | `oauth_service.handle_callback()` / `link_oauth_account()` |

### API

- `GET /api/auth/audit-logs?limit=100&user_id=&event_type=`（admin only）

---

## ファイル一覧

| ファイル | 説明 |
|---------|------|
| `app/core/auth/__init__.py` | パッケージ初期化 |
| `app/core/auth/password_policy.py` | パスワードポリシー |
| `app/core/auth/rate_limiter.py` | レート制限 + ロックアウト |
| `app/core/auth/audit.py` | 監査ログ |
| `app/models/login_attempt.py` | LoginAttempt モデル |
| `app/models/auth_audit_log.py` | AuthAuditLog モデル |
| `app/crud/login_attempt.py` | LoginAttempt CRUD |
| `app/crud/auth_audit_log.py` | AuthAuditLog CRUD |
| `tests/test_auth_security.py` | テスト（27件） |

## テスト

| テストクラス | ケース数 | 内容 |
|-------------|---------|------|
| TestPasswordPolicy | 8 | min/max/uppercase/lowercase/digit/special/valid |
| TestPasswordPolicyIntegration | 3 | create_user/change_password/reset_password |
| TestRateLimiting | 4 | under_limit/at_limit/recording |
| TestAccountLockout | 4 | locked_rejected/lock_after_max/admin_unlock/expired |
| TestSessionInvalidation | 3 | password_change/valid_session/inactive_user |
| TestAuditLogging | 5 | login_success/failure/password_change/admin_endpoint/non_admin |
