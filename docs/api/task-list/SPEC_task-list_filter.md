# Task List フィルタ機能 設計書

> Task List 画面にフィルタ機能を追加する。サーバーサイドの done 除外 + クライアントサイドの即時フィルタのハイブリッド方式。

---

## 1. 概要

### 1.1 背景

現在の Task List 画面はタブ（My Items / All Items）の切り替えのみで、
アイテム数が増えると目的のアイテムを見つけにくくなっている。
ステータス・カテゴリ・キーワード等でフィルタリングする機能が必要。

### 1.2 データ増加の課題

done アイテムは蓄積される一方で減らない。運用が進むと大半が done になる。

```
現在:    open 3 + in_progress 3 + done 4   = 10件（done 40%）
6ヶ月後: open 10 + in_progress 5 + done 150 = 165件（done 91%）
1年後:   open 10 + in_progress 5 + done 300 = 315件（done 95%）
```

日常で見たいのは open + in_progress（アクティブ）であり、done は「たまに確認したい」程度。
全件を毎回ロードするのは非効率。

### 1.3 方針: ハイブリッドフィルタ

| 層 | 役割 | 対象 |
|----|------|------|
| **サーバーサイド** | done 除外（デフォルト） | `status` クエリパラメータ |
| **クライアントサイド** | 即時フィルタ | ステータス（active 内）、カテゴリ、キーワード |

**デフォルト動作**: API は `status=open&status=in_progress` でアクティブのみ取得。
「Show Done」チェック ON 時のみ done を含めて再取得する。

---

## 2. サーバーサイド変更

### 2.1 API クエリパラメータ追加

`GET /api/task-list/mine` と `GET /api/task-list/all` に `status` パラメータを追加。

| パラメータ | 型 | デフォルト | 説明 |
|-----------|------|----------|------|
| `status` | List[str] | なし（全件） | 指定ステータスのみ返却。複数指定可 |

**リクエスト例**:
```
GET /api/task-list/mine?status=open&status=in_progress   → active のみ
GET /api/task-list/mine                                   → 全件（done 含む）
```

### 2.2 CRUD 変更

`get_assigned_items()` と `get_all_items()` に `statuses` 引数を追加。

```python
def get_assigned_items(
    db: Session, user_id: int, statuses: Optional[List[str]] = None
) -> List[TaskListItem]:
    q = db.query(TaskListItem).filter(TaskListItem.assignee_id == user_id)
    if statuses:
        q = q.filter(TaskListItem.status.in_(statuses))
    return q.order_by(...).all()
```

`get_all_items()` も同様に `statuses` 引数を追加。

### 2.3 変更の後方互換性

`status` パラメータ省略時は従来通り全件返却。既存の動作を壊さない。

---

## 3. フィルタ項目

| フィルタ | 層 | UI 部品 | 対象フィールド | 動作 |
|---------|------|---------|--------------|------|
| Show Done | サーバー | チェックボックス | `status` | OFF: active のみ取得 / ON: 全件取得 |
| ステータス | クライアント | ボタングループ | `status` | All / open / in_progress（Show Done 時は done も選択可） |
| カテゴリ | クライアント | ドロップダウン | `category_id` | 全カテゴリ / 特定カテゴリ |
| キーワード | クライアント | テキスト入力 | `title`, `backlog_ticket_id` | 部分一致（大文字小文字無視） |

### 3.1 Show Done チェックボックス

- **OFF（デフォルト）**: API に `?status=open&status=in_progress` を送信。ステータスボタンは All / Open / In Progress の 3 択
- **ON**: API にステータスパラメータなしで送信（全件取得）。ステータスボタンに Done が追加される

トグル時に API を再リクエストしてデータを再取得する。

### 3.2 ステータスフィルタ（クライアントサイド）

Show Done OFF 時:
- **All**（デフォルト）: open + in_progress 全表示
- **Open**: open のみ
- **In Progress**: in_progress のみ

Show Done ON 時:
- 上記に加え **Done**: done のみ

### 3.3 カテゴリフィルタ

- **All Categories**（デフォルト）: 全カテゴリ表示
- 各カテゴリ名: そのカテゴリのアイテムのみ

既存の `categoryMap`（`loadCategories()` で取得済み）を利用。

### 3.4 キーワードフィルタ

- `title` と `backlog_ticket_id` の両方を対象に部分一致検索
- 大文字・小文字を区別しない
- 入力イベント（`input`）で即時フィルタ（デバウンス 300ms）

---

## 4. UI 設計

### 4.1 レイアウト

```
[タブ: My Items | All Items]
[フィルタバー: Status(ボタン群) | Category(select) | Search(input) | ☐ Show Done]
[テーブル]
```

フィルタバーはタブとテーブルの間に配置。1行に収まるインラインレイアウト。

### 4.2 HTML 構造

```html
<div class="d-flex gap-2 align-items-center mb-3 flex-wrap" id="filter-bar">
    <!-- Status filter -->
    <div class="btn-group btn-group-sm" id="status-filter">
        <button class="btn btn-outline-secondary active" data-status="">All</button>
        <button class="btn btn-outline-secondary" data-status="open">Open</button>
        <button class="btn btn-outline-primary" data-status="in_progress">In Progress</button>
        <!-- Done button: hidden by default, shown when showDone is checked -->
        <button class="btn btn-outline-success d-none" data-status="done" id="btn-filter-done">Done</button>
    </div>
    <!-- Category filter -->
    <select class="form-select form-select-sm" id="filter-category" style="width:auto;">
        <option value="">All Categories</option>
    </select>
    <!-- Keyword search -->
    <input type="text" class="form-control form-control-sm"
           id="filter-keyword" placeholder="Search title / ticket..."
           style="max-width:220px;">
    <!-- Show Done toggle -->
    <div class="form-check form-check-inline ms-auto mb-0">
        <input class="form-check-input" type="checkbox" id="show-done">
        <label class="form-check-label small" for="show-done">Show Done</label>
    </div>
</div>
```

### 4.3 レスポンシブ

- `flex-wrap` により画面幅が狭い場合は折り返し
- Show Done チェックボックスは `ms-auto` で右寄せ
- 各フィルタ部品は `sm` サイズで統一

---

## 5. JavaScript 設計

### 5.1 フィルタ状態

```javascript
let showDone = false;         // Show Done checkbox state
let filterStatus = '';        // '' = All, 'open', 'in_progress', 'done'
let filterCategoryId = '';    // '' = All, or category id as string
let filterKeyword = '';       // free text
```

### 5.2 データ取得フロー

```javascript
async function loadItems() {
    let url;
    if (currentTab === 'mine') {
        url = '/api/task-list/mine';
    } else {
        url = '/api/task-list/all';
    }
    // Server-side: exclude done by default
    if (!showDone) {
        url += (url.includes('?') ? '&' : '?') + 'status=open&status=in_progress';
    }
    currentItems = await api.get(url);
    applyFilters();
}
```

### 5.3 クライアントサイドフィルタ

```javascript
function applyFilters() {
    let filtered = currentItems;

    if (filterStatus) {
        filtered = filtered.filter(item => item.status === filterStatus);
    }
    if (filterCategoryId) {
        filtered = filtered.filter(item =>
            item.category_id === parseInt(filterCategoryId));
    }
    if (filterKeyword) {
        const kw = filterKeyword.toLowerCase();
        filtered = filtered.filter(item =>
            item.title.toLowerCase().includes(kw) ||
            (item.backlog_ticket_id && item.backlog_ticket_id.toLowerCase().includes(kw))
        );
    }

    renderItems(filtered);
}
```

### 5.4 イベントハンドリング

| 部品 | イベント | 動作 |
|------|---------|------|
| Show Done チェック | `change` | `showDone` 更新 → Done ボタン表示/非表示 → `loadItems()`（API 再リクエスト） |
| ステータスボタン | `click` | `filterStatus` 更新 → `applyFilters()` |
| カテゴリ select | `change` | `filterCategoryId` 更新 → `applyFilters()` |
| キーワード input | `input` | 300ms デバウンス → `filterKeyword` 更新 → `applyFilters()` |

### 5.5 Show Done トグル時の動作

```javascript
function toggleShowDone() {
    showDone = document.getElementById('show-done').checked;
    // Show/hide Done button in status filter
    document.getElementById('btn-filter-done').classList.toggle('d-none', !showDone);
    // If currently filtering by 'done' but unchecking, reset status filter
    if (!showDone && filterStatus === 'done') {
        filterStatus = '';
        // Reset active button to All
    }
    loadItems();  // Re-fetch from server
}
```

### 5.6 タブ切り替え時の動作

`switchTab()` で API から新データ取得後、現在のフィルタ状態を維持して `applyFilters()` を呼ぶ。
フィルタはタブ切り替え時にリセットしない。

### 5.7 カテゴリフィルタの初期化

`loadCategories()` 内でモーダルの select と共に、フィルタ用 select（`#filter-category`）にもオプションを追加する。

---

## 6. 変更対象ファイル

### 6.1 バックエンド（3 ファイル）

| ファイル | 変更内容 |
|---------|---------|
| `app/routers/api_task_list.py` | `list_mine`, `list_all` に `status` クエリパラメータ追加 |
| `app/services/task_list_service.py` | `list_mine`, `list_all` に `statuses` 引数を透過 |
| `app/crud/task_list_item.py` | `get_assigned_items`, `get_all_items` に `statuses` フィルタ追加 |

### 6.2 フロントエンド（2 ファイル）

| ファイル | 変更内容 |
|---------|---------|
| `templates/task_list.html` | フィルタバー HTML 追加（タブとテーブルの間） |
| `static/js/task_list.js` | フィルタ状態変数、`applyFilters()`、イベントハンドラ、デバウンス、`loadItems()` 変更 |

---

## 7. テスト

### 7.1 API テスト（`tests/test_task_list.py` に追加）

| # | テストケース |
|---|------------|
| 1 | `GET /mine` パラメータなし → 全件返却（後方互換） |
| 2 | `GET /mine?status=open&status=in_progress` → done 除外 |
| 3 | `GET /mine?status=done` → done のみ返却 |
| 4 | `GET /all?status=open` → open のみ返却 |
| 5 | `GET /all?status=open&status=in_progress` → active のみ返却 |

### 7.2 手動確認項目

| # | 確認項目 |
|---|---------|
| 1 | デフォルト表示: done アイテムが表示されないこと |
| 2 | Show Done ON: done アイテムが表示されること、Done ボタンが出現すること |
| 3 | Show Done OFF: Done ボタンが消え、done で絞り込み中なら All にリセットされること |
| 4 | ステータスフィルタ: 各ステータスで正しく絞り込まれること |
| 5 | カテゴリフィルタ: 選択カテゴリのアイテムのみ表示されること |
| 6 | キーワードフィルタ: タイトル・チケット番号で部分一致検索できること |
| 7 | 複合フィルタ: ステータス + カテゴリ + キーワードの組み合わせが正しく動作すること |
| 8 | タブ切替: フィルタ状態が維持されること |
| 9 | 該当なし: フィルタ結果が 0 件の場合「No items found」が表示されること |
