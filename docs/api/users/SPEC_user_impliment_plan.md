# ユーザ管理機能 実装計画

## Context

現在のユーザ管理は API のみ（一覧・詳細・作成）で、更新・削除・パスワード変更がなく、管理UIも存在しない。
管理者がブラウザからユーザの作成・編集・有効/無効切替・ロール変更・パスワードリセットを行えるようにする。
一般ユーザは自分のパスワード変更のみ可能とする。

---

## 1. バックエンド変更

### 1-1. スキーマ追加 (`app/schemas/user.py`)

```python
class UserUpdate(BaseModel):
    display_name: Optional[str] = None
    role: Optional[str] = None       # admin のみ変更可
    is_active: Optional[bool] = None  # admin のみ変更可

class PasswordChange(BaseModel):
    current_password: str
    new_password: str

class PasswordReset(BaseModel):  # admin用
    new_password: str
```

### 1-2. CRUD追加 (`app/crud/user.py`)

| 関数 | 説明 |
|------|------|
| `update_user(db, user_id, data: dict)` | 部分更新（display_name, role, is_active） |
| `update_password(db, user_id, password_hash)` | パスワードハッシュ更新 |
| `delete_user(db, user_id)` | ユーザ削除 |

### 1-3. サービス追加 (`app/services/user_service.py`)

| 関数 | 説明 |
|------|------|
| `update_user(db, user_id, data, current_user_id)` | 管理者: 全フィールド編集可（自分の role/is_active は変更不可）。一般ユーザー: 自分の display_name のみ編集可 |
| `change_password(db, user_id, current_password, new_password)` | 現パスワード検証 → 新パスワードハッシュ化 → 更新 |
| `reset_password(db, user_id, new_password)` | admin用。パスワード強制リセット |
| `delete_user(db, user_id, current_user_id)` | admin のみ。自分自身の削除は不可 |

### 1-4. ルーター追加 (`app/routers/api_users.py`)

| メソッド | パス | 権限 | 説明 |
|---------|------|------|------|
| `PUT` | `/api/users/{id}` | 認証済（認可はサービス層） | ユーザ情報更新（管理者: 全フィールド / 一般: 自分のdisplay_nameのみ） |
| `DELETE` | `/api/users/{id}` | admin | ユーザ削除 |
| `PUT` | `/api/users/{id}/password` | admin | パスワードリセット |
| `PUT` | `/api/users/me/password` | 認証済 | 自分のパスワード変更 |

---

## 2. フロントエンド

### 2-1. ユーザ管理ページ (`templates/users.html`)

- ユーザ一覧テーブル（ID, Email, 表示名, ロール, 状態, アクション）
- 「ユーザ追加」ボタン → モーダル（email, display_name, password, role）（admin のみ表示）
- 管理者: 各行に「編集」「パスワードリセット」「削除」ボタン表示
- 一般ユーザー: 自分の行のみ「編集」ボタン表示（display_nameのみ変更可）
- 管理者用編集モーダル（email, display_name, role, is_active）
- 一般ユーザー用編集モーダル（display_nameのみ表示）
- パスワードリセットモーダル（new_password）
- 削除確認モーダル
- 既存UIパターン踏襲: Bootstrap 5 モーダル + `api.js` + `showToast`

### 2-2. JS (`static/js/users.js`)

- `loadUsers()` → テーブル描画
- `createUser()` / `updateUser()` / `deleteUser()` / `resetPassword()`
- ロール/状態のバッジ表示

### 2-3. パスワード変更（ナビバー `base.html`）

- ユーザドロップダウンに「パスワード変更」リンク追加
- パスワード変更モーダルを `base.html` に追加（全ページ共通）
- `changeMyPassword()` → `PUT /api/users/me/password`

### 2-4. ナビバー (`base.html`)

- ナビに「Users」リンク追加（Alerts の後）
- 管理画面アクセスは全認証ユーザーに許可し、操作ボタン（追加・編集・削除）のみ admin でJS側非表示

### 2-5. ページルーティング (`app/routers/pages.py`)

- `GET /users` → `users.html`

---

## 3. テスト (`tests/test_users.py` に追記)

### TestUserUpdate (~5件)
- `test_admin_update_user_display_name` — display_name 変更
- `test_admin_update_user_role` — role 変更
- `test_admin_update_user_deactivate` — is_active=false
- `test_update_user_not_found` — 404
- `test_admin_cannot_deactivate_self` — 自分の is_active 変更拒否

### TestUserDelete (~3件)
- `test_admin_delete_user` — ユーザ削除 204
- `test_delete_user_not_found` — 404
- `test_admin_cannot_delete_self` — 自分自身の削除拒否

### TestPasswordChange (~4件)
- `test_change_own_password` — 正常変更
- `test_change_password_wrong_current` — 現パスワード不一致 → 400
- `test_admin_reset_password` — admin がパスワードリセット
- `test_non_admin_cannot_reset_others_password` — 非admin拒否 403

### TestUserSelfEdit (~5件)
- `test_non_admin_can_edit_own_display_name` — 200
- `test_non_admin_cannot_edit_own_role` — 403
- `test_non_admin_cannot_edit_own_is_active` — 403
- `test_non_admin_cannot_edit_other_user` — 403
- `test_non_admin_cannot_edit_own_email` — 403

### TestUserUpdateRBAC (~1件)
- `test_non_admin_cannot_delete_user` — 403

---

## 4. 変更ファイル一覧

| ファイル | 変更内容 |
|---------|---------|
| `app/schemas/user.py` | UserUpdate, PasswordChange, PasswordReset 追加 |
| `app/crud/user.py` | update_user, update_password, delete_user 追加 |
| `app/services/user_service.py` | update_user, change_password, reset_password, delete_user 追加 |
| `app/routers/api_users.py` | PUT/DELETE エンドポイント追加 |
| `app/routers/pages.py` | `/users` ページ追加 |
| `templates/users.html` | **新規** — ユーザ管理ページ |
| `static/js/users.js` | **新規** — ユーザ管理JS |
| `templates/base.html` | Users ナビリンク + パスワード変更モーダル追加 |
| `tests/test_users.py` | ~14件のテスト追加 |

---

## 5. 実装順序

| ステップ | 内容 |
|---------|------|
| 1 | スキーマ追加（UserUpdate, PasswordChange, PasswordReset） |
| 2 | CRUD追加（update_user, update_password, delete_user） |
| 3 | サービス追加（update_user, change_password, reset_password, delete_user） |
| 4 | ルーター追加（PUT/DELETE エンドポイント 4本） |
| 5 | テスト追加 + 全テスト通過確認 |
| 6 | フロントエンド（users.html + users.js + base.html更新 + pages.py） |
| 7 | lint + ブラウザ確認 |

---

## 6. 検証手順

1. `pytest tests/test_users.py -v` — 新規 ~14件 + 既存 9件 = ~23件パス
2. `pytest tests/ -q` — 全テスト通過（185 + 14 = ~199件）
3. `ruff check . && ruff format --check .`
4. ブラウザ確認:
   - `/users` でユーザ一覧表示
   - ユーザ追加・編集・削除・パスワードリセット動作
   - ナビバーのパスワード変更モーダル動作
   - 非adminでログイン → 管理操作ボタンが非表示

---

## 7. 実装後の不具合修正

ブラウザ確認で登録・修正・削除ボタンが動作しない問題を発見し修正。

### 7-1. `/api/auth/me` が `role` を返さない問題

**原因**: `LoginResponse` スキーマに `role` フィールドがなく、`users.js` の `init()` で `currentUserRole` が常に `null` → admin 操作ボタンが非表示のまま。

**修正**:
- `app/schemas/auth.py`: `LoginResponse` に `role: str = "user"` 追加
- `app/routers/api_auth.py`: `login` / `me` エンドポイントのレスポンスに `role=user.role` 追加

### 7-2. ユーザ登録時にロールが設定されない問題

**原因**: `UserCreate` スキーマに `role` フィールドがなく、UI のロール選択が無視される。CRUD の `create_user` も `role` を User モデルにセットしていない。

**修正**:
- `app/schemas/user.py`: `UserCreate` に `role: str = "user"` 追加
- `app/crud/user.py`: `create_user` で `role=data.role` を設定

### 修正後の変更ファイル（追加分）

| ファイル | 変更内容 |
|---------|---------|
| `app/schemas/auth.py` | `LoginResponse` に `role` フィールド追加 |
| `app/routers/api_auth.py` | login/me レスポンスに `role` 追加 |
| `app/schemas/user.py` | `UserCreate` に `role` フィールド追加 |
| `app/crud/user.py` | `create_user` で `role` を設定 |
