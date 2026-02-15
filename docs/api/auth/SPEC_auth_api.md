# Auth API 仕様 (`/api/auth`)

> 本ドキュメントは [SPEC_API.md](./SPEC_API.md) から分割された認証 API の仕様です。
> 全体仕様は [SPEC.md](./SPEC.md) を参照してください。

---

## 概要

認証 API はセッションベースのログイン・ログアウト・現在ユーザー取得を提供する。
全エンドポイントが認証不要（パブリック）。

| メソッド | パス | 説明 | ステータスコード |
|---------|------|------|----------------|
| POST | `/api/auth/login` | ログイン | 200 / 401 |
| POST | `/api/auth/logout` | ログアウト | 204 |
| GET | `/api/auth/me` | ログインユーザー取得 | 200 / 401 |

---

## POST /api/auth/login

ログイン認証を行い、セッションを開始する。

### リクエストボディ: `LoginRequest`

| フィールド | 型 | 必須 | 説明 |
|------------|-----|------|------|
| email | string (EmailStr) | Yes | メールアドレス |
| password | string | Yes | パスワード |

### レスポンス

- **成功**: `200 OK` - `LoginResponse`
- **エラー**: `401 Unauthorized` - メールアドレス/パスワード不一致、アカウント無効

### 処理フロー

1. `auth_service.authenticate()` でメール・パスワード検証
2. `is_active=False` の場合 → `AuthenticationError("Account is disabled")`
3. 成功 → `session["user_id"]`, `session["display_name"]` を設定
4. `LoginResponse` を返却

---

## POST /api/auth/logout

セッションをクリアしてログアウトする。

### レスポンス

- **成功**: `204 No Content`

### 処理フロー

1. `request.session.clear()` でセッション破棄

---

## GET /api/auth/me

現在のログインユーザー情報を取得する。

### レスポンス

- **成功**: `200 OK` - `LoginResponse`
- **エラー**: `401 Unauthorized` - 未ログイン

### 処理フロー

1. セッションから `user_id` を取得
2. セッションなし → `401 Unauthorized`
3. ユーザーが DB に存在しない → セッションクリア + `401 Unauthorized`
4. ユーザー情報を `LoginResponse` で返却

---

## スキーマ

### LoginRequest

| フィールド | 型 | 必須 | 説明 |
|------------|-----|------|------|
| email | string (EmailStr) | Yes | メールアドレス |
| password | string | Yes | パスワード |

### LoginResponse

| フィールド | 型 | 説明 |
|------------|-----|------|
| user_id | integer | ユーザーID |
| email | string | メールアドレス |
| display_name | string | 表示名 |
| role | string | ロール (admin/user) |

---

## 認証方式

- **セッションベース認証**: Starlette `SessionMiddleware` + 署名付き Cookie
- **パスワードハッシュ**: bcrypt（`passlib[bcrypt]`）
- **セッション署名**: `itsdangerous` による `SECRET_KEY` ベースの署名

### 認証ミドルウェア

| アクセス先 | 未認証時の動作 |
|-----------|--------------|
| API パス (`/api/*`) | `401 Unauthorized` |
| ページパス (`/*`) | `/login` にリダイレクト（302） |

### パブリックパス（認証不要）

- `/login`
- `/static/*`
- `/api/auth/*`
- `POST /api/logs/`
- `/ws/*`

### CSRF 保護

状態変更メソッド（`POST`, `PUT`, `PATCH`, `DELETE`）に対して Origin/Referer ヘッダーを検証する `csrf_middleware` が適用される。

---

## 実装ファイル

| ファイル | 役割 |
|---------|------|
| `app/schemas/auth.py` | `LoginRequest`, `LoginResponse` スキーマ |
| `app/services/auth_service.py` | 認証ロジック（`authenticate`） |
| `app/routers/api_auth.py` | Auth REST API（3 エンドポイント） |
| `app/core/security.py` | パスワードハッシュ・検証（passlib + bcrypt） |
| `app/core/deps.py` | `get_current_user_id` 依存関数 |
| `main.py` | `SessionMiddleware`, `auth_middleware`, `csrf_middleware` |
| `templates/login.html` | ログインページ（独立テンプレート） |

---

## テスト

`tests/test_auth.py` に 12 テストケース。

| テストケース | 検証内容 |
|-------------|---------|
| test_login_success | 正しい資格情報でログイン成功（200 + LoginResponse） |
| test_login_wrong_password | 誤パスワードで401 |
| test_login_unknown_user | 存在しないユーザーで401 |
| test_login_inactive_user | 無効化されたユーザーで401 |
| test_logout | ログアウト後204 |
| test_me_authenticated | ログイン後にユーザー情報取得 |
| test_me_unauthenticated | 未ログインでme取得時401 |
| test_api_without_auth_returns_401 | 認証なしでAPI呼び出し時401 |
| test_page_without_auth_redirects_to_login | 認証なしでページアクセス時302リダイレクト |
| test_logs_post_is_public | ログPOST APIは認証不要で201 |
| test_logs_get_requires_auth | ログGET APIは認証必要（401） |
| test_login_page_is_public | ログインページは認証不要で200 |
