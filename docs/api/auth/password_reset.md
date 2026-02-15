# パスワードリセット機能 設計書

## 概要

ログインパスワードを忘れたユーザーが、メールアドレスを入力してパスワードをリセットできる機能。
トークンベースのリセットフロー（SMTP メール送信）を採用。

## ユーザーフロー

```
1. ログイン画面 → 「Forgot your password?」リンク
2. /forgot-password 画面 → メールアドレス入力 → 送信
3. POST /api/auth/forgot-password → トークン生成 → メール送信
4. ユーザーがメールのリンクをクリック
5. /reset-password?token=xxx 画面 → トークン検証 → 新パスワード入力
6. POST /api/auth/reset-password → パスワード更新 → ログイン画面へ
```

## セキュリティ設計

- **ユーザー列挙防止**: メール存在の有無に関わらず常に同じレスポンスを返却
- **トークン保護**: DB にはSHA-256ハッシュのみ保存（DB漏洩対策）
- **レート制限**: 15分間に最大3回まで（`PASSWORD_RESET_MAX_REQUESTS`）
- **トークン有効期限**: 30分（`PASSWORD_RESET_EXPIRY_MINUTES`）
- **リセット後の無効化**: 全トークン無効化 + 全セッション失効（`session_version` インクリメント）
- **アカウントアンロック**: リセット成功時に `locked_until = None`

## DB モデル

### password_reset_tokens テーブル

| カラム | 型 | 制約 | 説明 |
|--------|-----|------|------|
| id | Integer | PK | ID |
| user_id | Integer | FK(users.id, CASCADE), INDEX | ユーザーID |
| token_hash | String(255) | NOT NULL, UNIQUE | SHA-256ハッシュ |
| is_used | Boolean | NOT NULL, DEFAULT false | 使用済みフラグ |
| created_at | DateTime(TZ) | DEFAULT now() | 作成日時 |
| expires_at | DateTime(TZ) | NOT NULL | 有効期限 |

## 設定値

| 設定 | デフォルト | 説明 |
|------|-----------|------|
| PASSWORD_RESET_EXPIRY_MINUTES | 30 | トークン有効期限（分） |
| PASSWORD_RESET_COOLDOWN_MINUTES | 15 | レート制限ウィンドウ（分） |
| PASSWORD_RESET_MAX_REQUESTS | 3 | ウィンドウ内最大リクエスト数 |
| PASSWORD_RESET_BASE_URL | http://localhost:8000 | リセットURL のベース |
| SMTP_HOST | "" | SMTPサーバー（空=メール送信無効） |
| SMTP_PORT | 587 | SMTPポート |
| SMTP_USERNAME | "" | SMTP認証ユーザー |
| SMTP_PASSWORD | "" | SMTP認証パスワード |
| SMTP_FROM_ADDRESS | noreply@example.com | 送信元アドレス |
| SMTP_USE_TLS | true | STARTTLS使用 |
| SMTP_USE_SSL | false | SSL使用 |

## API エンドポイント

### POST /api/auth/forgot-password

リセットメールを送信する。

- **認証**: 不要
- **リクエスト**: `{ "email": "user@example.com" }`
- **レスポンス**: 常に `200 OK` `{ "detail": "..." }`
- **備考**: ユーザーの存在有無に関わらず同じレスポンス

### POST /api/auth/validate-reset-token

トークンの有効性を検証する。

- **認証**: 不要
- **リクエスト**: `{ "token": "..." }`
- **レスポンス**: `200 OK` `{ "valid": true/false }`

### POST /api/auth/reset-password

パスワードをリセットする。

- **認証**: 不要
- **リクエスト**: `{ "token": "...", "new_password": "..." }`
- **レスポンス**: `200 OK` / `400 Bad Request`（ポリシー違反）/ `404 Not Found`（トークン不正）

## ファイル構成

| ファイル | 説明 |
|---------|------|
| `app/models/password_reset_token.py` | PasswordResetToken モデル |
| `app/crud/password_reset_token.py` | トークン CRUD |
| `app/services/email_service.py` | SMTP メール送信（汎用） |
| `app/services/password_reset_service.py` | パスワードリセット ビジネスロジック |
| `app/schemas/auth.py` | ForgotPasswordRequest, ResetPasswordRequest, ValidateTokenRequest |
| `app/routers/api_auth.py` | 3エンドポイント追加 |
| `app/routers/pages.py` | /forgot-password, /reset-password ページ |
| `templates/forgot_password.html` | リセット要求画面 |
| `templates/reset_password.html` | パスワード再設定画面 |
| `tests/test_password_reset.py` | テスト（23件） |

## テスト

23件のテストケース:

- TestForgotPassword (5件): 既知メール, 未知メール, レート制限, 不正フォーマット, 非アクティブ
- TestValidateResetToken (4件): 有効, 期限切れ, 使用済み, 不正
- TestResetPassword (10件): 成功, アンロック, トークン無効化, セッション無効化, 期限切れ, 使用済み, 不正, 弱パスワード, 新パスワードログイン, 旧パスワード失敗
- TestForgotPasswordPages (4件): ページアクセス可, 認証不要確認
