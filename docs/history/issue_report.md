# ISSUE6 修正報告: タスクリスト — Start 後に Task Timer に表示されない

> 対象 ISSUE: [ISSUE6.md](./ISSUE6.md)

## 根本原因

Task List 画面の「Start」ボタンを押した際に **3つの問題** が連鎖して「タスクが表示されない」状態になっていた。

| # | 問題 | 影響 |
|---|------|------|
| A | `start_as_task` がタスク作成のみでタイマーを開始しない | Tasks ページで `pending` / `00:00:00` 表示。「開始した」のに動いていない |
| B | Start 後に Task List ページに留まる（Tasks ページに遷移しない） | ユーザーが Tasks ページ (`/tasks`) に移動しないと作成されたタスクを確認できない |
| C | 新規アイテムが「My Items」に表示されない | `assignee_id=NULL` で作成されるため、デフォルトタブに表示されず Start ボタンに辿り着けない |
| D | Start ボタンが `in_progress` でも残る | 二重 Start で重複タスクが作成される |

---

## 修正サマリー

| # | 修正内容 | 対象ファイル |
|---|----------|-------------|
| 6-A | **Start 時にタイマーを自動開始**（`status=in_progress` + `TaskTimeEntry` 作成） | `app/services/task_list_service.py` |
| 6-B | **Start 後に Tasks ページ (`/tasks`) に自動遷移** | `static/js/task_list.js` |
| 6-C | 新規作成時に `assignee_id = currentUserId` を自動設定 | `static/js/task_list.js` |
| 6-D | Start ボタンを `status === 'open'` の場合のみ表示 + バックエンドガード | `static/js/task_list.js`, `app/services/task_list_service.py` |
| 6-E | 未割当アイテムの Start 時に `assignee_id` を自動設定 | `app/services/task_list_service.py` |

---

## 修正詳細

### 6-A: タイマー自動開始（主修正）

**ファイル**: `app/services/task_list_service.py` — `start_as_task()`

```python
# 修正前: タスク作成のみ（status=pending, タイマーなし）
task = Task(user_id=user_id, title=item.title, ...)
db.add(task)

# 修正後: タスク作成 + タイマー自動開始
task = Task(user_id=user_id, title=item.title, ..., status="in_progress")
db.add(task)
db.flush()
entry = TaskTimeEntry(task_id=task.id, started_at=datetime.now(timezone.utc))
db.add(entry)
```

**効果**: Task List の Start 押下で、Tasks ページにタイマーが稼働中の状態でタスクが表示される。

---

### 6-B: Tasks ページへの自動遷移

**ファイル**: `static/js/task_list.js` — `startAsTask()`

```javascript
// 修正前: トースト表示してTask Listに留まる
showToast(`Task "${escapeHtml(task.title)}" created in Tasks`, 'success');
loadItems();

// 修正後: Tasks ページに遷移
window.location.href = '/tasks';
```

**効果**: Start 後に自動的に Tasks ページに遷移し、作成されたタスクを即座に確認できる。

---

### 6-C: 新規作成時の自動担当設定

**ファイル**: `static/js/task_list.js` — `saveItem()`

```javascript
// 修正後: 新規作成時に自分を担当に設定
if (!id) {
    data.assignee_id = currentUserId;
}
```

---

### 6-D: Start ボタン表示条件 + バックエンドガード

**フロントエンド**: `static/js/task_list.js`

```javascript
// 修正前: notDone (in_progress でも Start 表示)
const notDone = item.status !== 'done';

// 修正後: open のみ Start 表示
const isOpen = item.status === 'open';
```

**バックエンド**: `app/services/task_list_service.py`

```python
if item.status != "open":
    raise ConflictError("Item is already started")
```

---

### 6-E: Start 時の自動割当

```python
if item.assignee_id is None:
    item.assignee_id = user_id
```

---

## テスト結果

### テストケース（26件全通過）

| テスト | 状態 | 内容 |
|--------|------|------|
| `test_start_creates_task` | 更新 | `status == "in_progress"` の検証を追加 |
| `test_start_auto_starts_timer` | **新規** | Start 時に TimeEntry が作成され `stopped_at=None`（タイマー稼働中）を確認 |
| `test_start_task_appears_in_tasks_api` | 更新 | `GET /api/tasks/` にタスクが `in_progress` で表示されることを確認 |
| `test_start_already_started_returns_conflict` | 既存 | 2回目 Start が 400 を返すことを確認 |
| `test_start_auto_assigns_unassigned_item` | 既存 | 未割当アイテムの Start で `assignee_id` が設定されることを確認 |

### 実行結果

```
tests/test_task_list.py  — 26 passed
tests/test_tasks.py      — 33 passed
────────────────────────────
合計                       59 passed, 0 failed
```

---

## 修正ファイル一覧

| ファイル | 変更種別 |
|----------|---------|
| `app/services/task_list_service.py` | 修正（タイマー自動開始 + ガード + 自動割当） |
| `static/js/task_list.js` | 修正（Tasks 遷移 + 自動担当 + Start ボタン条件） |
| `templates/task_list.html` | 修正（JS キャッシュバスト v3→v4） |
| `tests/test_task_list.py` | 修正（テスト更新 + 新規テスト2件追加） |

## ユーザー操作フロー（修正後）

1. Task List 画面で「New Item」→ **自動的に自分に割り当て** → My Items に表示
2. 「Start」ボタンをクリック
3. **自動的に Tasks ページ (`/tasks`) に遷移**
4. **タイマーが稼働中の状態** でタスクカードが表示される
