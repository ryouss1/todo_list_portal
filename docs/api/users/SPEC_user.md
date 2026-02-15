# User・認証 機能仕様書

> ユーザー管理・認証・認可機能の完全な仕様。ユーザー CRUD・セッションベース認証・RBAC（ロールベースアクセス制御）・パスワード管理・CSRF 保護を含む。

---

## 1. 概要

### 1.1 背景

システム全体のユーザー管理と認証基盤を提供する機能。セッションベースの認証、管理者/一般ユーザーのロール制御、パスワードのハッシュ管理を行う。

### 1.2 目的

- ユーザーの CRUD 管理（Admin のみ作成・削除可能）
- セッションベース認証（`SessionMiddleware` + 署名付き Cookie）
- RBAC: `admin` / `user` ロールによるアクセス制御
- 自己編集: 一般ユーザーは自身の `display_name` のみ変更可能
- パスワード変更（自分）/ リセット（Admin）
- CSRF 保護（Origin / Referer ヘッダー検証）
- デフォルトユーザーの自動シード

### 1.3 基本フロー

```
[認証フロー]
ログインページ (/login)
    ↓ email + password
POST /api/auth/login → auth_service.authenticate()
    ↓ 成功
session["user_id"] = user.id → / にリダイレクト

[ユーザー管理フロー]
Admin → POST /api/users/ → ユーザー作成（password → bcrypt ハッシュ）
Admin → PUT /api/users/{id} → ユーザー情報更新（role, is_active, display_name, email）
User  → PUT /api/users/{id} → 自分の display_name のみ変更可能
Admin → DELETE /api/users/{id} → ユーザー削除（自分自身は不可）
```

### 1.4 主要用語

| 用語 | 説明 |
|------|------|
| Admin | `role="admin"` のユーザー。ユーザー作成・削除・他ユーザー編集が可能 |
| User | `role="user"` のユーザー。自身の `display_name` のみ編集可能 |
| Session | `SessionMiddleware` による署名付き Cookie ベースのセッション |
| CSRF | Origin/Referer ヘッダーによるクロスサイトリクエストフォージェリ防止 |
| Seed | アプリケーション起動時のデフォルトユーザー自動作成 |

---

## 2. データモデル

### 2.1 User テーブル

| カラム | 型 | 制約 | 説明 |
|--------|-----|------|------|
| `id` | Integer | PK, AUTO | ユーザー ID |
| `email` | String(255) | NOT NULL, UNIQUE | メールアドレス（ログイン ID） |
| `display_name` | String(200) | NOT NULL | 表示名 |
| `password_hash` | String(255) | NULL 許容 | bcrypt ハッシュ |
| `role` | String(20) | NOT NULL, server_default `"user"` | ロール（`admin` / `user`） |
| `is_active` | Boolean | default `True` | アクティブ状態（`False` でログイン不可） |
| `default_preset_id` | Integer | FK → `attendance_presets.id` | デフォルト勤怠プリセット |
| `created_at` | DateTime(TZ) | server_default `now()` | 作成日時 |
| `updated_at` | DateTime(TZ) | server_default `now()`, onupdate | 更新日時 |

### 2.2 ER 図

```
attendance_presets (1) ----< (0..*) users
                                default_preset_id FK

users (1) ----< (0..*) todos           (user_id)
users (1) ----< (0..*) attendances     (user_id)
users (1) ----< (0..*) tasks           (user_id)
users (1) ----< (0..*) presence_statuses (user_id, UNIQUE)
users (1) ----< (0..*) daily_reports   (user_id)
users (1) ----< (0..*) task_list_items (assignee_id, created_by)
users (1) ----< (0..*) alerts          (acknowledged_by)
```

---

## 3. API エンドポイント

### 3.1 Auth API (`/api/auth`) — 全て認証不要

| メソッド | パス | 説明 |
|---------|------|------|
| `POST` | `/api/auth/login` | ログイン |
| `POST` | `/api/auth/logout` | ログアウト |
| `GET` | `/api/auth/me` | 現在のユーザー情報取得 |

#### POST /api/auth/login

リクエスト:

| フィールド | 型 | 必須 |
|-----------|-----|------|
| `email` | EmailStr | Yes |
| `password` | str | Yes |

処理:
1. `auth_service.authenticate()` でメール・パスワード検証
2. `is_active=False` の場合 → `AuthenticationError("Account is disabled")`
3. 成功 → `session["user_id"]`, `session["display_name"]` を設定

レスポンス: `LoginResponse`（`user_id`, `email`, `display_name`, `role`）

#### POST /api/auth/logout

`request.session.clear()` でセッション破棄。レスポンス: 204

#### GET /api/auth/me

セッションから `user_id` を取得し、ユーザー情報を返す。
- セッションなし → 401
- ユーザーが DB に存在しない → セッションクリア + 401

### 3.2 User API (`/api/users`)

| メソッド | パス | 認可 | 説明 |
|---------|------|------|------|
| `GET` | `/api/users/` | 認証ユーザー | ユーザー一覧 |
| `POST` | `/api/users/` | **Admin のみ** | ユーザー作成 |
| `PUT` | `/api/users/me/password` | 認証ユーザー | 自分のパスワード変更 |
| `GET` | `/api/users/{id}` | 認証ユーザー | ユーザー詳細 |
| `PUT` | `/api/users/{id}` | 認証ユーザー（権限チェックあり） | ユーザー更新 |
| `DELETE` | `/api/users/{id}` | **Admin のみ** | ユーザー削除 |
| `PUT` | `/api/users/{id}/password` | **Admin のみ** | パスワードリセット |

> `PUT /api/users/me/password` は `/{user_id}` より前にルート定義（FastAPI のパスマッチング順序）

---

## 4. スキーマ定義

### 4.1 Auth スキーマ

**LoginRequest:**

| フィールド | 型 | 必須 |
|-----------|-----|------|
| `email` | EmailStr | Yes |
| `password` | str | Yes |

**LoginResponse:**

| フィールド | 型 | デフォルト |
|-----------|-----|----------|
| `user_id` | int | - |
| `email` | str | - |
| `display_name` | str | - |
| `role` | str | `"user"` |

### 4.2 User スキーマ

**UserCreate:**

| フィールド | 型 | デフォルト | 必須 |
|-----------|-----|----------|------|
| `email` | EmailStr | - | Yes |
| `display_name` | str | - | Yes |
| `password` | str | - | Yes |
| `role` | str | `"user"` | No |

**UserUpdate:**

| フィールド | 型 | 必須 |
|-----------|-----|------|
| `display_name` | str | No |
| `email` | EmailStr | No |
| `role` | str | No |
| `is_active` | bool | No |

全フィールド Optional。`exclude_unset=True` で部分更新。

**UserResponse:** `id`, `email`, `display_name`, `role`, `is_active`, `created_at`, `updated_at`

> `password_hash` はレスポンスに含まれない

**PasswordChange:**

| フィールド | 型 | 必須 |
|-----------|-----|------|
| `current_password` | str | Yes |
| `new_password` | str | Yes |

**PasswordReset:**

| フィールド | 型 | 必須 |
|-----------|-----|------|
| `new_password` | str | Yes |

---

## 5. 認証

### 5.1 セッション管理

```python
app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY)
```

- Starlette の `SessionMiddleware` を使用
- 署名付き Cookie（`session` Cookie）にセッションデータを格納
- `SECRET_KEY` で署名（環境変数で設定）

### 5.2 認証サービス (`auth_service.authenticate`)

```python
def authenticate(db, email, password) -> User:
    user = get_user_by_email(db, email)
    if not user or not user.password_hash:
        raise AuthenticationError("Invalid email or password")
    if not verify_password(password, user.password_hash):
        raise AuthenticationError("Invalid email or password")
    if not user.is_active:
        raise AuthenticationError("Account is disabled")
    return user
```

チェック順序:
1. メールアドレスでユーザー検索
2. `password_hash` が未設定 → 認証エラー
3. パスワード照合（bcrypt）
4. `is_active` チェック → 無効アカウントは拒否

### 5.3 パスワードハッシュ (`app/core/security.py`)

```python
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
```

- `passlib` + `bcrypt` を使用（`bcrypt < 4.1` の互換性要件あり）
- `hash_password(password)` → bcrypt ハッシュ生成
- `verify_password(plain, hashed)` → 照合

### 5.4 Auth ミドルウェア (`auth_middleware`)

```python
public_prefixes = ("/login", "/static/", "/api/auth/", "/api/logs/", "/ws/")
```

- パブリックパス → 認証スキップ
- API パス（`/api/`）で未認証 → そのまま通過（個別エンドポイントの `Depends` で 401）
- ページパスで未認証 → `/login` にリダイレクト（302）

### 5.5 CSRF ミドルウェア (`csrf_middleware`)

状態変更メソッド（`POST`, `PUT`, `PATCH`, `DELETE`）に対して:
1. `Origin` ヘッダーがあれば `Host` と比較
2. `Referer` ヘッダーがあれば `Host` と比較
3. 不一致の場合 → 403（`"CSRF check failed"`）

---

## 6. 認可（RBAC）

### 6.1 依存関数

**`get_current_user_id(request)`** — `app/core/deps.py`
- `request.session["user_id"]` を返す
- 未設定 → `AuthenticationError`（401）
- テスト時はオーバーライド可能

**`require_admin(user_id, db)`** — `app/core/deps.py`
- `get_current_user_id` に依存
- DB からユーザー取得し、`role == "admin"` を確認
- Admin でない → `ForbiddenError("Admin access required")`（403）

### 6.2 権限マトリクス

| 操作 | Admin | User | 未認証 |
|------|-------|------|--------|
| ログイン・ログアウト・me | - | - | OK |
| ユーザー一覧・詳細 | OK | OK | 401 |
| ユーザー作成 | OK | 403 | 401 |
| ユーザー削除 | OK（自分以外） | 403 | 401 |
| ユーザー更新（他ユーザー） | OK | 403 | 401 |
| ユーザー更新（自分） | display_name, email（role/is_active 不可） | display_name のみ | 401 |
| パスワード変更（自分） | OK | OK | 401 |
| パスワードリセット（他ユーザー） | OK | 403 | 401 |

### 6.3 ユーザー更新の認可ロジック

```python
def update_user(db, user_id, data, current_user_id):
    is_admin = current_user.role == "admin"
    is_self = user_id == current_user_id

    if not is_admin:
        if not is_self:
            raise ForbiddenError("Cannot edit other users")
        # Non-admin: display_name のみ許可
        update_data = {k: v for k, v in update_data.items() if k in {"display_name"}}
        if not update_data:
            raise ForbiddenError("Cannot change these fields")
    else:
        # Admin editing self: role と is_active は変更不可
        if is_self and ("role" in update_data or "is_active" in update_data):
            raise ForbiddenError("Cannot change own role or active status")
```

| 操作者 | 対象 | 許可フィールド |
|--------|------|--------------|
| Admin | 他ユーザー | `display_name`, `email`, `role`, `is_active` |
| Admin | 自分 | `display_name`, `email`（`role`, `is_active` は不可） |
| User | 自分 | `display_name` のみ |
| User | 他ユーザー | 全て不可（403） |

---

## 7. パスワード管理

### 7.1 パスワード変更（自分）

`PUT /api/users/me/password`

1. `current_password` で現在のパスワードを検証
2. 不一致 → `ConflictError("Current password is incorrect")`（400）
3. 一致 → `new_password` を bcrypt ハッシュして保存

### 7.2 パスワードリセット（Admin）

`PUT /api/users/{id}/password`

- Admin のみ実行可能
- 現在のパスワード検証なし
- `new_password` を bcrypt ハッシュして保存

### 7.3 パスワード保存

- DB カラム: `password_hash` (String 255, NULL 許容)
- ハッシュ形式: `$2b$...`（bcrypt）
- レスポンスには `password`, `password_hash` いずれも含まれない

---

## 8. デフォルトユーザーシード

### 8.1 `seed_default_user()`

アプリケーション起動時（`lifespan`）に実行。

```python
# app/config.py
DEFAULT_USER_ID = 1
DEFAULT_EMAIL = "admin@example.com"
DEFAULT_DISPLAY_NAME = "Admin"
DEFAULT_PASSWORD = "admin"
```

動作:
1. `User.id == DEFAULT_USER_ID` を検索
2. 存在しない → 新規作成（`role="admin"`, パスワードハッシュ済み）
3. 存在する → 以下を自動修正:
   - `password_hash` が未設定 → デフォルトパスワードでハッシュ設定
   - `role != "admin"` → `"admin"` に修正
   - `email != DEFAULT_EMAIL` → 更新

---

## 9. フロントエンド

### 9.1 ログインページ (`/login`)

- 独立テンプレート（`base.html` を継承しない）
- Bootstrap 5.3.3 + Bootstrap Icons
- Email + Password フォーム
- `fetch('/api/auth/login')` で JSON POST
- 成功 → `window.location.href = '/'`
- 失敗 → アラートメッセージ表示

### 9.2 セッション連携

- `api.js` が全 API レスポンスで 401 を検出 → `/login` にリダイレクト
- ログアウト: ナビバーのユーザーメニューから `POST /api/auth/logout`
- `GET /api/auth/me` でページ読み込み時に現在ユーザー情報を取得

### 9.3 WebSocket 認証

全 WebSocket エンドポイント（`/ws/logs`, `/ws/presence`, `/ws/alerts`）:

```python
def _ws_get_user_id(websocket):
    return websocket.session.get("user_id", 0)

# 接続時
if not _ws_get_user_id(websocket):
    await websocket.close(code=4401, reason="Not authenticated")
```

---

## 10. ビジネスルール

### 10.1 ユーザーライフサイクル

```
作成 (Admin) → is_active=True, role="user"
    ↓
更新 → display_name, email, role, is_active 変更可能（権限に応じて）
    ↓
無効化 → is_active=False（ログイン不可、データは残る）
    ↓
削除 (Admin) → 物理削除（自分自身は削除不可）
```

### 10.2 重複メール防止

- `email` カラムに UNIQUE 制約
- `create_user()` で `IntegrityError` → `ConflictError("Email already exists")`

### 10.3 自己削除防止

- `delete_user()` で `user_id == current_user_id` → `ForbiddenError("Cannot delete yourself")`

### 10.4 Admin 自己保護

Admin が自分自身を編集する際、以下は変更不可:
- `role`（自分で Admin 権限を剥奪するのを防止）
- `is_active`（自分でアカウントを無効化するのを防止）

### 10.5 ロール値

| ロール | 説明 |
|--------|------|
| `admin` | 管理者。全操作が可能（一部自己操作を除く） |
| `user` | 一般ユーザー。読み取り + 自身の display_name 編集のみ |

- server_default は `"user"`
- デフォルトユーザーは `"admin"` で作成

---

## 11. ファイル構成

| ファイル | 役割 |
|---------|------|
| `app/models/user.py` | `User` モデル定義 |
| `app/schemas/user.py` | User スキーマ（Create, Update, Response, PasswordChange, PasswordReset） |
| `app/schemas/auth.py` | Auth スキーマ（LoginRequest, LoginResponse） |
| `app/crud/user.py` | User DB アクセス（CRUD + password update） |
| `app/services/user_service.py` | ユーザービジネスロジック（CRUD + 認可チェック + パスワード管理） |
| `app/services/auth_service.py` | 認証ロジック（`authenticate`） |
| `app/core/security.py` | パスワードハッシュ・検証（passlib + bcrypt） |
| `app/core/deps.py` | `get_current_user_id`, `require_admin` 依存関数 |
| `app/core/exceptions.py` | `AuthenticationError`（401）, `ForbiddenError`（403） |
| `app/routers/api_users.py` | User REST API（7 エンドポイント） |
| `app/routers/api_auth.py` | Auth REST API（3 エンドポイント） |
| `app/init_db.py` | `seed_default_user()` + `seed_default_presets()` + `seed_default_categories()` |
| `app/config.py` | `DEFAULT_USER_ID`, `DEFAULT_EMAIL`, `DEFAULT_PASSWORD`, `SECRET_KEY` |
| `main.py` | `SessionMiddleware`, `auth_middleware`, `csrf_middleware`, WebSocket 認証 |
| `templates/login.html` | ログインページ（独立テンプレート） |
| `tests/test_users.py` | User API テスト（28 テスト） |
| `tests/test_auth.py` | Auth API テスト（12 テスト） |

---

## 12. テスト

### 12.1 User API テスト（`tests/test_users.py` — 28 テスト）

**TestUserAPI (8 テスト):**

| テスト | 検証内容 |
|--------|---------|
| `test_list_users` | ユーザー一覧取得、デフォルトユーザー存在確認 |
| `test_create_user` | ユーザー作成 + デフォルト値 + レスポンスにパスワードなし |
| `test_create_user_password_hashed` | DB にハッシュ保存（`$2b$` で始まる） |
| `test_create_user_missing_password` | パスワード未指定 → 422 |
| `test_create_user_duplicate_email` | 重複メール → 400/409/500 |
| `test_get_user` | 個別取得 |
| `test_get_user_not_found` | 存在しない ID → 404 |
| `test_user_response_includes_role` | レスポンスに `role` フィールド |

**TestUserRBAC (2 テスト):**

| テスト | 検証内容 |
|--------|---------|
| `test_non_admin_cannot_create_user` | 非 Admin → 403 |
| `test_non_admin_can_list_users` | 非 Admin でも一覧取得は 200 |

**TestUserUpdate (5 テスト):**

| テスト | 検証内容 |
|--------|---------|
| `test_admin_update_user_display_name` | Admin が他ユーザーの display_name 変更 |
| `test_admin_update_user_role` | Admin が他ユーザーの role 変更 |
| `test_admin_update_user_deactivate` | Admin が他ユーザーを無効化 |
| `test_update_user_not_found` | 存在しない ID → 404 |
| `test_admin_cannot_deactivate_self` | Admin が自分を無効化 → 403 |

**TestUserSelfEdit (5 テスト):**

| テスト | 検証内容 |
|--------|---------|
| `test_non_admin_can_edit_own_display_name` | 自分の display_name 変更 → 200 |
| `test_non_admin_cannot_edit_own_role` | 自分の role 変更 → 403 |
| `test_non_admin_cannot_edit_own_is_active` | 自分の is_active 変更 → 403 |
| `test_non_admin_cannot_edit_other_user` | 他ユーザー編集 → 403 |
| `test_non_admin_cannot_edit_own_email` | 自分の email 変更 → 403 |

**TestUserDelete (3 テスト):**

| テスト | 検証内容 |
|--------|---------|
| `test_admin_delete_user` | Admin によるユーザー削除 |
| `test_delete_user_not_found` | 存在しない ID → 404 |
| `test_admin_cannot_delete_self` | 自分の削除 → 403 |

**TestPasswordChange (4 テスト):**

| テスト | 検証内容 |
|--------|---------|
| `test_change_own_password` | 自分のパスワード変更 |
| `test_change_password_wrong_current` | 現在のパスワード不一致 → 400 |
| `test_admin_reset_password` | Admin によるパスワードリセット |
| `test_non_admin_cannot_reset_others_password` | 非 Admin が他ユーザーのリセット → 403 |

**TestUserUpdateRBAC (1 テスト):**

| テスト | 検証内容 |
|--------|---------|
| `test_non_admin_cannot_delete_user` | 非 Admin のユーザー削除 → 403 |

### 12.2 Auth テスト（`tests/test_auth.py` — 12 テスト）

**TestAuthLogin (4 テスト):**

| テスト | 検証内容 |
|--------|---------|
| `test_login_success` | 正常ログイン（user_id, email, display_name 確認） |
| `test_login_wrong_password` | パスワード不一致 → 401 |
| `test_login_unknown_user` | 存在しないユーザー → 401 |
| `test_login_inactive_user` | 無効アカウント → 401（`"disabled"` メッセージ） |

**TestAuthLogout (1 テスト):**

| テスト | 検証内容 |
|--------|---------|
| `test_logout` | ログアウト → 204 |

**TestAuthMe (2 テスト):**

| テスト | 検証内容 |
|--------|---------|
| `test_me_authenticated` | 認証済み → ユーザー情報返却 |
| `test_me_unauthenticated` | 未認証 → 401 |

**TestAuthMiddleware (5 テスト):**

| テスト | 検証内容 |
|--------|---------|
| `test_api_without_auth_returns_401` | API 未認証 → 401 |
| `test_page_without_auth_redirects_to_login` | ページ未認証 → 302 リダイレクト |
| `test_logs_post_is_public` | `POST /api/logs/` は認証不要 |
| `test_logs_get_requires_auth` | `GET /api/logs/` は認証必要 |
| `test_login_page_is_public` | `/login` は認証不要 |

---

## 13. マイグレーション

| リビジョン | 説明 | 依存 |
|-----------|------|------|
| `53797f9c29e5` | 初期スキーマ（users テーブル含む） | - |
| `7e3eabbd85e8` | `password_hash` カラム追加 | `53797f9c29e5` |
| `b3f1a2c4d5e6` | `username` → `email` カラムリネーム（String 100→255） | `709a8464bb48` |
| `47696373217f` | `role` カラム追加（server_default `"user"`） | `82739a6351f7` |
| `620335984593` | `attendance_presets` テーブル + `users.default_preset_id` FK | ... |

### カラム変遷

```
初期: id, username(100), display_name, is_active, created_at, updated_at
  ↓ 7e3eabbd85e8
+ password_hash (String 255, nullable)
  ↓ b3f1a2c4d5e6
username → email (String 255)
  ↓ 47696373217f
+ role (String 20, server_default "user", NOT NULL)
  ↓ 620335984593
+ default_preset_id (FK → attendance_presets.id)
```
