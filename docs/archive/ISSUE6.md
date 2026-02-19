# ISSUE6: タスクリスト画面 — 新規作成アイテムが表示されない＆Start関連の不具合

> 報告: タスクを開始しても Task リストに表示されない

## ステータス: **全件修正完了** ✅

| # | 重要度 | 概要 | ステータス |
|---|--------|------|-----------|
| 6-1 | **高** | 新規作成アイテムがデフォルトタブ「My Items」に表示されない | ✅ 修正済み |
| 6-2 | 中 | Start 後もボタンが残り、同一アイテムから複数 Task が作成される | ✅ 修正済み |
| 6-3 | 低 | `start_as_task` が `assignee_id` を自動設定しない | ✅ 修正済み |

### 修正内容サマリー

| # | 修正ファイル | 修正内容 |
|---|-------------|---------|
| 6-1 | `static/js/task_list.js` `saveItem()` | 新規作成時に `data.assignee_id = currentUserId` を追加 |
| 6-2 | `static/js/task_list.js` レンダリング | Start ボタン表示条件を `notDone` → `isOpen`（`item.status === 'open'`）に変更 |
| 6-2 | `app/services/task_list_service.py` `start_as_task()` | `item.status != "open"` で `ConflictError` を返す + `count_by_source_item_id` による DB レベル重複チェック |
| 6-2 | `static/js/task_list.js` `startAsTask()` | クリック時にボタンを即座に `disabled` にして二重クリック防止 |
| 6-3 | `app/services/task_list_service.py` `start_as_task()` | `item.assignee_id is None` の場合に `item.assignee_id = user_id` を自動設定 |

### テスト更新

- 旧 `test_start_multiple_times`（複数 Start を許容）→ 削除
- 新規テスト追加:
  - `test_start_already_started_returns_conflict` — 2回目の Start が 400 エラーを返すことを検証
  - `test_start_auto_assigns_unassigned_item` — 未割当アイテムの Start で自動割当されることを検証
  - `test_start_with_existing_task_returns_conflict` — DB レベル重複チェックの検証（レースコンディション対策）
  - `test_done_restart_after_done` — Done 後に再 Start できることを検証（正常系）

---

---

## 調査結果詳細

## 6-1: 新規作成アイテムが「My Items」に表示されない（主要因） ✅ 修正済み

### 現象

1. Task List 画面で「New Item」ボタン → モーダルで Title 等を入力 → Save
2. アイテムが作成される（API は 201 を返す）
3. **しかしデフォルトタブ「My Items」にアイテムが表示されない**
4. 「All Items」タブに切り替えると表示される

### 原因

**フロントエンド（`task_list.js`）の `saveItem()` が `assignee_id` を送信していない。**

```javascript
// static/js/task_list.js:155-164
async function saveItem() {
    const data = {
        title: ...,
        description: ...,
        scheduled_date: ...,
        category_id: ...,
        backlog_ticket_id: ...,
        // ← assignee_id が含まれていない！
    };
```

- `TaskListItemCreate` スキーマの `assignee_id` はデフォルト `None`
- 結果、アイテムは常に **未割当 (assignee_id=NULL)** で作成される
- デフォルトタブ「My Items」は `GET /api/task-list/mine` → `assignee_id == user_id` でフィルタ
- **未割当アイテムは「My Items」に表示されない**

### 影響範囲

- `static/js/task_list.js` — `saveItem()` 関数（行 155-174）
- `templates/task_list.html` — モーダルに `assignee_id` の入力フィールドがない

### 修正案

新規作成時にログインユーザーを自動的に `assignee_id` に設定する:

```javascript
// saveItem() 内、新規作成時
if (!id) {
    data.assignee_id = currentUserId;  // 自分に割り当て
}
```

---

## 6-2: Start 後もボタンが残り、重複 Task が作成される ✅ 修正済み

### 現象

1. Task List アイテムの「Start」ボタンをクリック
2. Task が作成され、アイテムの status が `in_progress` に変更される
3. **しかし Start ボタンがまだ表示される**
4. 再度 Start をクリックすると **別の Task が作成される**（重複）

### 原因

#### フロントエンド: Start ボタンの表示条件が不十分

```javascript
// task_list.js:86-103 — Mine タブ
if (notDone) {  // notDone = item.status !== 'done'
    // in_progress でも notDone=true → Start ボタンが表示される
    actions += `<button ... onclick="startAsTask(${item.id})">Start</button>`;
}

// task_list.js:101-103 — All タブ
if (notDone && item.assignee_id) {
    // 同様に in_progress でもボタンが表示される
    actions += `<button ... onclick="startAsTask(${item.id})">Start</button>`;
}
```

`notDone` は `status !== 'done'` であるため、`in_progress` でも `true` になる。

#### バックエンド: 重複チェックがない

```python
# app/services/task_list_service.py:85-101
def start_as_task(db, item_id, user_id):
    item = _get_visible_item(db, item_id, user_id)
    # ← item.status == "in_progress" のチェックがない
    task = Task(user_id=user_id, ...)
    db.add(task)
    item.status = "in_progress"
    db.commit()
```

**注意**: `test_start_multiple_times` テストが意図的に複数回 Start を許容している（行 219-227）。仕様確認が必要。

### 修正案

**A. フロントエンド**: Start ボタンを `status === 'open'` の場合のみ表示

```javascript
// Mine タブ
if (item.status === 'open') {
    actions += `<button ... onclick="startAsTask(${item.id})">Start</button>`;
}
```

**B. バックエンド（任意）**: `in_progress` 状態のアイテムへの再 Start を拒否

```python
def start_as_task(db, item_id, user_id):
    item = _get_visible_item(db, item_id, user_id)
    if item.status != "open":
        raise ConflictError("Item is already started")
```

---

## 6-3: `start_as_task` が `assignee_id` を自動設定しない ✅ 修正済み

### 現象

API 経由（または All Items タブで他ユーザーの割当アイテムを Start）で未割当アイテムを Start した場合、Task は作成されるがアイテムの `assignee_id` は `NULL` のまま。

### 原因

```python
# app/services/task_list_service.py:85-101
def start_as_task(db, item_id, user_id):
    item = _get_visible_item(db, item_id, user_id)
    task = Task(user_id=user_id, ...)
    db.add(task)
    item.status = "in_progress"
    # ← item.assignee_id = user_id が設定されていない
    db.commit()
```

### 修正案

Start 時に未割当なら自動的に割り当てる:

```python
def start_as_task(db, item_id, user_id):
    item = _get_visible_item(db, item_id, user_id)
    task = Task(user_id=user_id, ...)
    db.add(task)
    item.status = "in_progress"
    if item.assignee_id is None:
        item.assignee_id = user_id  # 自動割当
    db.commit()
```

---

## 関連コード一覧

| ファイル | 行 | 内容 |
|----------|-----|------|
| `static/js/task_list.js` | 1 | `currentTab = 'mine'` — デフォルトタブ |
| `static/js/task_list.js` | 45-54 | `loadItems()` — mine/all の切り替え |
| `static/js/task_list.js` | 86-103 | Start ボタンの表示条件 |
| `static/js/task_list.js` | 155-174 | `saveItem()` — `assignee_id` 未送信 |
| `static/js/task_list.js` | 192-200 | `startAsTask()` — Start 処理 |
| `app/services/task_list_service.py` | 85-101 | `start_as_task()` — Task 作成 + status 変更 |
| `app/crud/task_list_item.py` | 32-38 | `get_assigned_items()` — Mine タブの取得クエリ |
| `app/schemas/task_list_item.py` | 7-13 | `TaskListItemCreate` — `assignee_id` デフォルト None |
| `templates/task_list.html` | 39-78 | モーダル — assignee_id 入力なし |
| `tests/test_task_list.py` | 219-227 | `test_start_multiple_times` — 複数 Start を許容するテスト |

## 再現手順（6-1）

1. `/task-list` にアクセス
2. 「New Item」ボタンをクリック → Title に適当な値を入力 → Save
3. 「My Items」タブに何も表示されない（テーブルが表示されない or "No items found"）
4. 「All Items」タブに切り替え → 作成したアイテムが表示される
