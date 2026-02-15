# SPEC: Group（グループ機能）

> **ステータス**: 設計段階
> **依存**: ユーザー管理機能（Phase 1）完了済み

---

## 1. 概要

### 1.1 目的

ユーザーをグループに分類し、組織構造を表現する。
将来的にグループ単位でのフィルタリング・集計・権限管理の基盤とする。

### 1.2 要件

| 項目 | 仕様 |
|------|------|
| グループ作成 | 管理者のみ |
| グループ編集・削除 | 管理者のみ |
| グループ参照 | 全認証ユーザー |
| ユーザーへの割当 | 管理者のみ（ユーザー編集で設定） |
| 所属数 | **1人1グループ**（所属なしも許可） |
| グループ削除時 | 所属ユーザーの `group_id` を NULL に戻す |

### 1.3 設計方針

- `Group` マスタテーブル + `users.group_id` FK で実装（中間テーブル不要）
- 1人1グループのため、User モデルに FK カラムを追加するだけでシンプルに実現
- グループ一覧は `sort_order` でソート可能（表示順制御）
- 論理削除ではなく物理削除（所属ユーザーの FK は SET NULL）

---

## 2. データモデル

### 2.1 Group テーブル（新規）

```
Table: groups

id          : Integer, PK, autoincrement
name        : String(100), NOT NULL, UNIQUE
description : String(500), nullable
sort_order  : Integer, NOT NULL, default=0
created_at  : DateTime(timezone=True), server_default=now()
```

### 2.2 users テーブル（カラム追加）

```
group_id    : Integer, FK(groups.id, ondelete=SET NULL), nullable, index
```

### 2.3 ER 図

```
groups (1) ──── (N) users.group_id (SET NULL)
```

---

## 3. API エンドポイント

### 3.1 グループ CRUD

| メソッド | パス | 権限 | 説明 |
|---------|------|------|------|
| `GET` | `/api/groups/` | 認証済 | グループ一覧（sort_order 順） |
| `POST` | `/api/groups/` | admin | グループ作成 |
| `PUT` | `/api/groups/{id}` | admin | グループ更新 |
| `DELETE` | `/api/groups/{id}` | admin | グループ削除（所属ユーザーの group_id を NULL に） |

### 3.2 ユーザーへのグループ割当

既存の `PUT /api/users/{id}` を拡張。`UserUpdate` スキーマに `group_id` を追加。

| メソッド | パス | 権限 | 説明 |
|---------|------|------|------|
| `PUT` | `/api/users/{id}` | admin（group_id 変更時） | `group_id` を設定（NULL で解除） |

- admin のみが `group_id` を変更可能
- 非 admin が `group_id` を送信した場合は無視（既存の `display_name` のみ許可ロジックで自然にフィルタ）

### 3.3 リクエスト・レスポンス

**GroupCreate**
```json
{
    "name": "開発チーム",
    "description": "ソフトウェア開発部門",
    "sort_order": 1
}
```

**GroupUpdate**
```json
{
    "name": "開発チーム（改名）",
    "description": "...",
    "sort_order": 2
}
```

**GroupResponse**
```json
{
    "id": 1,
    "name": "開発チーム",
    "description": "ソフトウェア開発部門",
    "sort_order": 1,
    "member_count": 3,
    "created_at": "2026-02-11T..."
}
```

**UserResponse（拡張）**
```json
{
    "id": 1,
    "email": "admin@example.com",
    "display_name": "管理者",
    "role": "admin",
    "is_active": true,
    "group_id": 1,
    "group_name": "開発チーム",
    "created_at": "...",
    "updated_at": "..."
}
```

---

## 4. スキーマ

### 4.1 新規スキーマ（`app/schemas/group.py`）

```python
class GroupCreate(BaseModel):
    name: str
    description: Optional[str] = None
    sort_order: int = 0

class GroupUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    sort_order: Optional[int] = None

class GroupResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    sort_order: int
    member_count: int = 0
    created_at: datetime

    model_config = {"from_attributes": True}
```

### 4.2 既存スキーマ変更

**`app/schemas/user.py` — UserUpdate**
```python
class UserUpdate(BaseModel):
    display_name: Optional[str] = None
    email: Optional[EmailStr] = None
    role: Optional[str] = None
    is_active: Optional[bool] = None
    group_id: Optional[int] = None          # 追加
```

**`app/schemas/user.py` — UserResponse**
```python
class UserResponse(BaseModel):
    id: int
    email: str
    display_name: str
    role: str
    is_active: bool
    group_id: Optional[int] = None          # 追加
    group_name: Optional[str] = None        # 追加（JOIN で取得）
    created_at: datetime
    updated_at: Optional[datetime] = None
```

---

## 5. バックエンド実装

### 5.1 モデル（`app/models/group.py`）

```python
class Group(Base):
    __tablename__ = "groups"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False, unique=True)
    description = Column(String(500), nullable=True)
    sort_order = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
```

### 5.2 User モデル変更（`app/models/user.py`）

```python
# 追加
group_id = Column(Integer, ForeignKey("groups.id", ondelete="SET NULL"), nullable=True, index=True)
```

### 5.3 CRUD（`app/crud/group.py`）

| 関数 | 説明 |
|------|------|
| `get_group(db, group_id)` | グループ取得 |
| `get_groups(db)` | 全グループ取得（sort_order 順） |
| `create_group(db, name, description, sort_order)` | グループ作成 |
| `update_group(db, group, data)` | グループ更新 |
| `delete_group(db, group)` | グループ削除 |
| `count_members(db, group_id)` | 所属ユーザー数 |

### 5.4 サービス（`app/services/group_service.py`）

| 関数 | 説明 |
|------|------|
| `list_groups(db)` | 一覧取得 + `member_count` 付与 |
| `create_group(db, data)` | 作成（名前重複 → `ConflictError`） |
| `update_group(db, group_id, data)` | 更新（名前重複 → `ConflictError`、存在チェック → `NotFoundError`） |
| `delete_group(db, group_id)` | 削除（存在チェック → `NotFoundError`） |

### 5.5 ルーター（`app/routers/api_groups.py`）

```python
router = APIRouter(prefix="/api/groups", tags=["groups"])

GET    /              → list_groups      (認証済)
POST   /              → create_group     (admin)
PUT    /{group_id}    → update_group     (admin)
DELETE /{group_id}    → delete_group     (admin)
```

### 5.6 User サービス変更

`user_service.update_user()` — admin の場合 `group_id` を許可フィールドに追加（既存ロジックで自然に対応）。

`user_service.list_users()` / `get_user()` — レスポンスに `group_name` を付与。

---

## 6. フロントエンド

### 6.1 ユーザー管理画面（`templates/users.html` + `static/js/users.js`）

既存のユーザー管理画面を拡張:

- ユーザー一覧テーブルに「グループ」列を追加
- 管理者用の編集モーダルに「グループ」セレクトボックスを追加
  - 選択肢: `-- なし --` + グループ一覧
- 非 admin はグループ選択不可（フィールド非表示）

### 6.2 グループ管理セクション（`static/js/users.js` に統合）

ユーザー管理画面にグループ管理タブまたはセクションを追加:

- グループ一覧テーブル（名前、説明、メンバー数、アクション）
- admin のみ: 追加・編集・削除ボタン表示
- インライン編集（TaskList と同パターン）または モーダル編集

### 6.3 他画面での活用（将来拡張）

グループ情報は以下の画面でフィルターとして活用可能（本フェーズでは実装しない）:

- Presence: グループ別フィルタ
- Calendar: グループ別表示切替
- Summary: グループ別集計

---

## 7. マイグレーション

```
alembic revision --autogenerate -m "add_groups_and_user_group_id"
alembic upgrade head
```

変更内容:
1. `groups` テーブル新規作成
2. `users.group_id` カラム追加 + インデックス + FK

---

## 8. シードデータ

`app/init_db.py` に `seed_default_groups()` を追加。

```python
DEFAULT_GROUPS = [
    (1, "開発チーム", "ソフトウェア開発", 1),
    (2, "営業チーム", "営業・顧客対応", 2),
    (3, "管理部", "総務・経理", 3),
]
```

- `setval` でシーケンスを調整（既存の categories / rooms パターンに準拠）

---

## 9. テスト（`tests/test_groups.py`）

### TestGroupCRUD (~7件)

| テスト | 説明 |
|--------|------|
| `test_list_groups` | シードデータ含む一覧取得 |
| `test_create_group_admin` | admin がグループ作成 → 201 |
| `test_create_group_non_admin` | 非 admin → 403 |
| `test_create_group_duplicate_name` | 名前重複 → 400 |
| `test_update_group` | admin が更新 → 200 |
| `test_delete_group` | admin が削除 → 204 |
| `test_delete_group_clears_user_group` | 削除時に所属ユーザーの group_id が NULL になる |

### TestUserGroup (~4件)

| テスト | 説明 |
|--------|------|
| `test_admin_assign_group` | admin が `PUT /api/users/{id}` で group_id 設定 |
| `test_admin_unassign_group` | admin が group_id=null で解除 |
| `test_non_admin_cannot_change_group` | 非 admin が group_id 変更 → 無視される |
| `test_user_response_includes_group_name` | UserResponse に group_name が含まれる |

---

## 10. 変更ファイル一覧

| ファイル | 変更 |
|---------|------|
| `app/models/group.py` | **新規** — Group モデル |
| `app/models/user.py` | `group_id` FK カラム追加 |
| `app/models/__init__.py` | Group インポート追加 |
| `app/schemas/group.py` | **新規** — GroupCreate/Update/Response |
| `app/schemas/user.py` | UserUpdate に `group_id`、UserResponse に `group_id` + `group_name` 追加 |
| `app/crud/group.py` | **新規** — Group CRUD |
| `app/services/group_service.py` | **新規** — Group サービス |
| `app/services/user_service.py` | `group_id` 許可 + `group_name` 付与 |
| `app/routers/api_groups.py` | **新規** — Group ルーター |
| `main.py` | ルーター登録 + `seed_default_groups()` 呼出 |
| `app/init_db.py` | `seed_default_groups()` 追加 |
| `alembic/versions/xxx.py` | **自動生成** — groups テーブル + users.group_id |
| `templates/users.html` | グループ列 + 管理セクション追加 |
| `static/js/users.js` | グループ CRUD + ユーザー編集にグループ選択追加 |
| `tests/test_groups.py` | **新規** — ~11件 |
| `docs/SPEC_GROUP.md` | 本ドキュメント |

---

## 11. 実装順序

| ステップ | 内容 |
|---------|------|
| 1 | モデル作成（Group + User に group_id）+ マイグレーション |
| 2 | シードデータ（seed_default_groups） |
| 3 | スキーマ作成（GroupCreate/Update/Response + UserUpdate/Response 拡張） |
| 4 | CRUD 作成（group.py） |
| 5 | サービス作成（group_service.py + user_service.py 変更） |
| 6 | ルーター作成（api_groups.py + main.py 登録） |
| 7 | テスト作成 + 全テスト通過確認 |
| 8 | フロントエンド（users.html + users.js 拡張） |
| 9 | lint + ブラウザ確認 |

---

## 12. 検証手順

1. `alembic upgrade head` — マイグレーション適用
2. `pytest tests/test_groups.py -v` — 新規 ~11件パス
3. `pytest tests/ -q` — 全テスト通過
4. `ruff check . && ruff format --check .`
5. ブラウザ確認:
   - `/users` でグループ列が表示される
   - グループ管理（作成・編集・削除）が動作する
   - ユーザー編集でグループ割当・解除が動作する
   - 非 admin ではグループ管理ボタンが非表示
