# Task List アイテム作成時の担当者設計（案C 確定）

> 対象ファイル: `docs/api/task-list/SPEC_task-list.md` セクション 6.3-6.5 の改訂
> 実装対象: `app/schemas/task_list_item.py`, `templates/task_list.html`, `static/js/task_list.js`

---

## 1. 現状の問題

### 1.1 バグ: 作成時に担当者が強制自己アサイン

`static/js/task_list.js` line 255:

```javascript
// 新規作成時に強制的に自分にアサイン → バグ
data.assignee_id = currentUserId;
await api.post('/api/task-list/', data);
```

- 作成モーダルに担当者フィールドが存在しない
- API 側（`TaskListItemCreate.assignee_id: Optional[int] = None`）は未割当に対応済み
- 結果として、未割当アイテム（チーム共有プール）を UI から作成できない

### 1.2 担当者変更が Update 経由でできない

`TaskListItemUpdate` に `assignee_id` フィールドがないため、
編集モーダルから担当者を変更できない（Assign/Unassign ボタンでしか操作できない）。

---

## 2. 決定した設計: 案C

### 設計方針

| 項目 | 決定内容 |
|------|---------|
| 作成時デフォルト | **未割当（Unassigned）** |
| 担当者セレクタ | **作成/編集モーダル両方に追加** |
| 他ユーザーへのアサイン | **許可**（チームバックログ管理のため） |
| Assign/Unassign ボタン | **維持**（モーダル外からの素早い操作用） |
| `TaskListItemUpdate.assignee_id` | **追加**（モーダル編集からの変更に必要） |
| バックエンド権限変更 | **なし** |

### 採用理由

本システムはチーム共有バックログが目的（SPEC 1.2）。
「未割当プール → 担当者決定 → 着手」という pull-based ワークフローに合わせ、
**作成時のデフォルトは未割当**とする。同時に、作成時に担当者を指定できる柔軟性も確保する。

---

## 3. 変更内容

### 3.1 作成モーダルの UI

```
┌─────────────────────────────────────┐
│ New Item                            │
├─────────────────────────────────────┤
│ Title *                             │
│ [                                 ] │
│                                     │
│ Description                         │
│ [                                 ] │
│                                     │
│ Scheduled Date      Category        │
│ [          ]        [-- None -- ▼] │
│                                     │
│ Assignee                            │
│ [-- Unassigned --               ▼] │  ← 追加（デフォルト: 未割当）
│                                     │
│ Backlog Ticket                      │
│ [                                 ] │
│                                     │
│            [Cancel] [Save]          │
└─────────────────────────────────────┘
```

**担当者ドロップダウンの選択肢**:
- 先頭: `-- Unassigned --`（value = `""`、assignee_id = null として送信）
- 以降: 全ユーザー一覧（既取得の `userMap` を利用）

### 3.2 編集モーダルの UI

同一モーダルを再利用。編集時は現在の担当者を初期値としてセット。
「未割当に戻す」も `-- Unassigned --` を選択することで可能。

### 3.3 バックエンドの変更

#### `app/schemas/task_list_item.py`

`TaskListItemUpdate` に `assignee_id` を追加：

```python
class TaskListItemUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    scheduled_date: Optional[date] = None
    category_id: Optional[int] = None
    backlog_ticket_id: Optional[str] = None
    assignee_id: Optional[int] = None   # 追加
    status: Optional[ItemStatusType] = None
```

`exclude_unset=True` の動作（CRUD 基底クラス `update` で使用）：
- 送信しない場合（省略）: 変更なし（`exclude_unset=True` で除外される）
- `assignee_id: null` を明示送信: null（未割当）に変更される
- `assignee_id: 5` を送信: user_id=5 に変更される

> **NOTE**: `null` は明示的に送信する必要があるため、
> JS 側で「Unassigned」を選択した場合は `assignee_id: null` を必ず送信する。

#### サービス層・CRUD・モデル・マイグレーション

変更不要。API は既に `assignee_id` を受け付けている。

### 3.4 フロントエンドの変更

#### `static/js/task_list.js`

1. `loadUsers()` で構築する `userMap` を担当者セレクタにも反映
2. `openNewItem()`: 担当者セレクタを `""` にリセット
3. `openEditItem()`: 担当者セレクタを `item.assignee_id || ""` にセット
4. `saveItem()`: セレクタの値を読み、`assignee_id` を送信
   - 新規作成: `assignee_id` を payload に含める（null or 選択ユーザー）
   - 編集: `assignee_id` を payload に含める（null or 選択ユーザー）
5. `data.assignee_id = currentUserId;` を削除

#### `templates/task_list.html`

モーダルに担当者 `<select>` を追加（Category の下）。

---

## 4. 作成後の遷移挙動

| 作成時の assignee_id | 表示されるタブ |
|--------------------|----------------|
| null（未割当） | All タブで確認可能（Mine タブには表示されない） |
| 自分 | Mine タブにすぐ表示される |
| 他ユーザー | All タブで確認できる |

作成後は現在のタブを `loadItems()` でリロードする（既存挙動を維持）。

---

## 5. 変更ファイル一覧

| ファイル | 変更内容 |
|---------|---------|
| `app/schemas/task_list_item.py` | `TaskListItemUpdate` に `assignee_id: Optional[int] = None` 追加 |
| `templates/task_list.html` | モーダルに担当者 `<select>` 追加（Category 下） |
| `static/js/task_list.js` | バグ修正（強制自己アサイン削除）+ 担当者セレクタ操作実装 |

---

## 6. テスト追加

| テストケース | 内容 |
|------------|------|
| 未割当で作成（明示） | `assignee_id` なしで POST → `assignee_id=null` で返却 |
| 他ユーザーへのアサインで作成 | `assignee_id=user2.id` で POST → 正常に作成 |
| PUT で担当者を変更 | `{"assignee_id": user_id}` → 担当者が変わる |
| PUT で担当者を解除 | `{"assignee_id": null}` → `assignee_id` が null になる |
