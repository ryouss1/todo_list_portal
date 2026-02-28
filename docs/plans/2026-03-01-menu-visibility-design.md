# メニュー表示 ON/OFF 機能 設計書

> 作成日: 2026-03-01

---

## 1. 概要

### 1.1 目的

- **一般メンバー**: 自分に許可されているメニューを自由に表示/非表示できる（自己サービス）
- **管理者**: ユーザー・ロール・部署ごとにメニューの表示/非表示を一元管理できる

### 1.2 設計方針

- ユーザーの自己設定は**最高優先度**（管理者は上書き不可）
- 既存の `user_menus` / `role_menus` テーブルを活用し、新たに `department_menus` テーブルを追加
- 現在 `role_menus` が表示判定に使われていないバグを同時修正

---

## 2. アーキテクチャ

### 2.1 新テーブル: `department_menus`

```sql
department_menus (
  department_id  INTEGER  PK, FK(departments.id, CASCADE)
  menu_id        INTEGER  PK, FK(menus.id, CASCADE)
  kino_kbn       SMALLINT NOT NULL, DEFAULT 1  -- 1=表示, 0=非表示
)
```

`role_menus` / `user_menus` と同じ構造。部署削除・メニュー削除時に CASCADE で連動削除。

### 2.2 メニュー表示判定の優先チェーン（更新後）

```
1. user_menus[user_id, menu_id] が存在する?
   → YES: kino_kbn の値をそのまま使用（最高優先度・上書き不可）
   → NO: 次へ

2. department_menus[user.department_id, menu_id] が存在する?
   → YES: kino_kbn の値を使用
   → NO: 次へ

3. role_menus[any_user_role, menu_id] が存在する? (※現在未使用を修正)
   → YES: kino_kbn=1 が1件でもあれば表示（OR評価）
   → NO: 次へ

4. required_resource が NULL?
   → YES: 全認証ユーザーに表示
   → NO: 次へ

5. user.role == "admin"?
   → YES: 表示（admin bypass）
   → NO: RBAC権限チェック（role_permissions）
```

**実装ファイル**: `portal_core/portal_core/crud/menu.py` — `get_visible_menus_for_user()`

### 2.3 新APIエンドポイント

| メソッド | パス | 説明 | 権限 |
|---------|------|------|------|
| GET | `/api/menus/{id}/role-visibility` | ロール×メニューの表示設定一覧 | admin |
| PUT | `/api/menus/{id}/role-visibility` | ロール別メニュー表示設定（一括） | admin |
| GET | `/api/menus/{id}/department-visibility` | 部署×メニューの表示設定一覧 | admin |
| PUT | `/api/menus/{id}/department-visibility` | 部署別メニュー表示設定（一括） | admin |
| GET | `/api/menus/{id}/user-visibility` | ユーザー別メニュー表示設定一覧 | admin |
| PUT | `/api/menus/{id}/user-visibility` | ユーザー別メニュー表示設定（admin） | admin |
| GET | `/api/menus/my-visibility` | 自分の表示設定一覧 | 認証済み |
| PUT | `/api/menus/my-visibility` | 自分の表示設定を更新（自己サービス） | 認証済み |

### 2.4 UIコンポーネントの配置

**管理者向け**: `/menus` ページに「表示設定」タブを追加
- サブタブ: ロール別 / 部署別 / ユーザー別
- 行=メニュー、列=ロール（部署/ユーザー）のマトリクス表 + トグルスイッチ

**一般ユーザー向け**: ナビバーのユーザードロップダウンに「メニュー設定」を追加
- モーダルでメニュー一覧 + 表示/非表示トグル
- 「リセット」ボタンで部署/ロール設定にフォールバック

---

## 3. データフロー・キャッシュ

### 3.1 ナビバー表示フロー

```
リクエスト受信
  → _get_filtered_nav_items(user_id)
  → キャッシュ(30秒TTL)にヒット? → YES: キャッシュ返却
  → NO: get_visible_menus_for_user(db, user_id) で評価
       → 結果をキャッシュに保存 → 返却
```

### 3.2 設定変更時のキャッシュ無効化

| 操作 | 無効化対象 |
|------|-----------|
| ユーザーが自分の設定を変更 | そのユーザーのキャッシュのみ |
| admin がユーザー別設定を変更 | 対象ユーザーのキャッシュのみ |
| admin がロール別設定を変更 | そのロールを持つ全ユーザーのキャッシュ |
| admin が部署別設定を変更 | その部署に属する全ユーザーのキャッシュ |

**実装**: `PortalApp._nav_cache` の対象エントリを削除（TTL満了を待たず即時反映）

### 3.3 自己サービス設定の制約

- ユーザーが非表示にできるのは「現在アクセス権限があるメニュー」のみ
- 既に非表示のメニューは操作不可（403 Forbidden）
- `user_menus.kino_kbn=0` を設定した場合、admin の部署/ロール設定は無視
- 「リセット」で `user_menus` レコードを削除 → 部署/ロール設定にフォールバック

### 3.4 エラーハンドリング

| ケース | 挙動 |
|--------|------|
| 存在しないメニューIDを指定 | 404 Not Found |
| 一般ユーザーが admin 専用メニューを設定 | 403 Forbidden |
| 非アクティブ部署の department_menus | 無視（is_active=false を除外） |

---

## 4. UI詳細

### 4.1 管理者向け（`/menus` ページ拡張）

```
[メニュー一覧] [表示設定]  ← タブ追加

表示設定タブ:
  [ロール別] [部署別] [ユーザー別]  ← サブタブ

  ロール別マトリクス例:
  ┌──────────────┬───────┬───────┬───────┐
  │ メニュー名   │ Admin │ Dev   │ Sales │
  ├──────────────┼───────┼───────┼───────┤
  │ Dashboard    │  ●    │  ●    │  ●    │
  │ Wiki         │  ●    │  ●    │  ○    │
  │ Logs         │  ●    │  ○    │  ○    │
  └──────────────┴───────┴───────┴───────┘
  ● = 表示(kino_kbn=1)  ○ = 非表示(0)  - = 未設定（RBAC判定）
```

トグル変更で即時 PUT API 呼び出し（自動保存）。

### 4.2 一般ユーザー向け（ナビバー）

ユーザードロップダウンに「メニュー設定」リンクを追加。

```
メニュー設定モーダル:
  ☑ Dashboard
  ☑ Task List
  ☐ Reports  ← 非表示に設定
  ☑ Wiki
  ...
  [リセット]    [保存]
```

保存後にキャッシュを無効化 → ページリロードでナビバーに即反映。

---

## 5. テスト方針

### 5.1 portal_core テスト

| テストファイル | 内容 | 追加件数（目安） |
|--------------|------|----------------|
| `test_menus_api.py` | role/department/user visibility API CRUD | +15件 |
| `test_crud_menus.py` | `get_visible_menus_for_user()` 優先チェーン検証 | +12件 |
| `test_nav_filtering.py` | department_menus / role_menus の反映確認 | +8件 |
| `test_nav_cache.py` | ロール/部署変更時のキャッシュ即時無効化 | +4件 |

### 5.2 前提

- 既存873テスト（258 portal_core + 615 app）が全パスであること

---

## 6. 変更ファイル一覧

| ファイル | 変更内容 |
|---------|---------|
| `alembic/versions/xxxx_add_department_menus.py` | `department_menus` テーブル追加 |
| `portal_core/portal_core/models/menu.py` | `DepartmentMenu` モデル追加 |
| `portal_core/portal_core/crud/menu.py` | `get_visible_menus_for_user()` 更新、role_menus 有効化、新CRUD関数追加 |
| `portal_core/portal_core/schemas/menu.py` | Visibility 系スキーマ追加 |
| `portal_core/portal_core/routers/api_menus.py` | visibility エンドポイント追加 |
| `portal_core/portal_core/templates/menus.html` | 「表示設定」タブ追加 |
| `portal_core/portal_core/templates/base.html` | ユーザードロップダウンに「メニュー設定」追加 |
| `portal_core/portal_core/static/js/menus.js` | 表示設定タブのマトリクス操作ロジック |
| `portal_core/portal_core/static/js/menu_settings.js` | ユーザー自己サービスモーダルのロジック（新規） |
| `portal_core/tests/test_menus_api.py` | visibility API テスト追加 |
| `portal_core/tests/test_crud_menus.py` | 優先チェーンテスト追加 |
| `portal_core/tests/test_nav_filtering.py` | 新チェーンの反映テスト追加 |
| `portal_core/tests/test_nav_cache.py` | キャッシュ無効化テスト追加 |

---

## 7. 技術的負債

| 項目 | 内容 |
|------|------|
| `role_menus` の未使用バグ | 現在 `get_visible_menus_for_user()` で `role_menus` が参照されていない。本実装で修正 |
| `department_menus` の将来拡張 | 部署階層（親部署の設定を子部署が継承）は将来課題として docs/issue に記録 |
