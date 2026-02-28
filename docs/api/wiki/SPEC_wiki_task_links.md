# WIKI タスク紐づけ設計書

> 本ドキュメントは [spec_wiki.md](../../spec_wiki.md) のサブ設計書です。
> 作成日: 2026-02-25

---

## 1. 概要

WIKIページとタスクを多対多（M:N）で紐づける機能。1つのページに複数のタスクを関連付け、逆に1つのタスクを複数ページから参照できる。

### 1.1 紐づけ対象の区別

| 対象テーブル | 性質 | 紐づけ種別 |
|-------------|------|-----------|
| `task_list_items` | 永続（バックログ）| **主要紐づけ** |
| `tasks` | 一時的（完了時に物理削除）| **補助紐づけ** |

`tasks` は `done` 操作で物理削除されるが、紐づけレコードは削除せず保持する。タスク削除時は `task_id` を NULL にして紐づけを維持し、スナップショット（`task_title`）で情報を保持する。

---

## 2. データベース設計

### 2.1 wiki_page_task_items テーブル（永続紐づけ）

WIKIページ ↔ タスクリストアイテム（task_list_items）の多対多中間テーブル。

| カラム名 | 型 | 制約 | 説明 |
|----------|-----|------|------|
| page_id | Integer | FK(wiki_pages.id, CASCADE), NOT NULL | WIKIページID |
| task_item_id | Integer | FK(task_list_items.id, CASCADE), NOT NULL | タスクリストアイテムID |
| linked_by | Integer | FK(users.id, SET NULL), NULL許可 | 紐づけ者ID |
| linked_at | DateTime(TZ) | DEFAULT now() | 紐づけ日時 |

- **主キー**: `(page_id, task_item_id)` 複合主キー
- ページ削除時: CASCADE で紐づけも削除
- タスクリストアイテム削除時: CASCADE で紐づけも削除

### 2.2 wiki_page_tasks テーブル（補助紐づけ）

WIKIページ ↔ タスク（tasks）の多対多中間テーブル。タスクが完了・削除されても紐づけレコードは保持し、`task_title` スナップショットで参照できるようにする。

| カラム名 | 型 | 制約 | 説明 |
|----------|-----|------|------|
| id | Integer | PK, AUTO_INCREMENT | 紐づけID |
| page_id | Integer | FK(wiki_pages.id, CASCADE), NOT NULL, INDEX | WIKIページID |
| task_id | Integer | FK(tasks.id, SET NULL), NULL許可, INDEX | タスクID（タスク削除時 NULL） |
| task_title | String(500) | NOT NULL | タスクタイトルのスナップショット（紐づけ時点で記録） |
| linked_by | Integer | FK(users.id, SET NULL), NULL許可 | 紐づけ者ID |
| linked_at | DateTime(TZ) | DEFAULT now() | 紐づけ日時 |

- **主キー**: `id`（サロゲートキー）
- **ユニーク制約**: `(page_id, task_id)` ※ task_id が NULL でない場合のみ（部分インデックス）
- ページ削除時: CASCADE で紐づけも削除
- タスク削除時（done操作含む）: `task_id` が **SET NULL**（紐づけレコードは残存）
- `task_title` により、タスク削除後も「完了済みタスク名」として UI で表示可能

### 2.3 ER 図

```
wiki_pages      (1) ──── (N) wiki_page_task_items.page_id    (CASCADE)
task_list_items (1) ──── (N) wiki_page_task_items.task_item_id (CASCADE)
users           (1) ──── (N) wiki_page_task_items.linked_by  (SET NULL)

wiki_pages (1) ──── (N) wiki_page_tasks.page_id   (CASCADE)
tasks      (1) ──── (N) wiki_page_tasks.task_id   (SET NULL ← タスク削除後も紐づけ保持)
users      (1) ──── (N) wiki_page_tasks.linked_by (SET NULL)
```

---

## 3. SQLAlchemy モデル

```python
# app/models/wiki_task_link.py

from sqlalchemy import Column, DateTime, ForeignKey, Integer, Table
from sqlalchemy.sql import func

from portal_core.database import Base

# wiki_pages ↔ task_list_items（永続）
wiki_page_task_items = Table(
    "wiki_page_task_items",
    Base.metadata,
    Column("page_id", Integer, ForeignKey("wiki_pages.id", ondelete="CASCADE"), primary_key=True),
    Column("task_item_id", Integer, ForeignKey("task_list_items.id", ondelete="CASCADE"), primary_key=True),
    Column("linked_by", Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
    Column("linked_at", DateTime(timezone=True), server_default=func.now()),
)

# wiki_pages ↔ tasks（補助紐づけ：タスク削除後も保持）
class WikiPageTask(Base):
    __tablename__ = "wiki_page_tasks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    page_id = Column(Integer, ForeignKey("wiki_pages.id", ondelete="CASCADE"), nullable=False, index=True)
    task_id = Column(Integer, ForeignKey("tasks.id", ondelete="SET NULL"), nullable=True, index=True)
    task_title = Column(String(500), nullable=False)  # スナップショット
    linked_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    linked_at = Column(DateTime(timezone=True), server_default=func.now())
```

WikiPage モデルへのリレーション追加:

```python
# app/models/wiki_page.py（抜粋）
from sqlalchemy.orm import relationship
from app.models.wiki_task_link import wiki_page_task_items, WikiPageTask

class WikiPage(Base):
    # ... 既存カラム定義 ...

    # task_list_items との多対多（中間テーブル方式）
    linked_task_items = relationship(
        "TaskListItem",
        secondary=wiki_page_task_items,
        back_populates="linked_wiki_pages",
        lazy="select",
    )
    # tasks との紐づけ（クラスベース中間テーブル方式 / SET NULL 対応）
    task_links = relationship(
        "WikiPageTask",
        back_populates="page",
        cascade="all, delete-orphan",
        lazy="select",
    )
```

---

## 4. Alembic マイグレーション

```python
# alembic/versions/xxxx_add_wiki_task_links.py

def upgrade():
    # wiki_page_task_items（永続紐づけ）
    op.create_table(
        "wiki_page_task_items",
        sa.Column("page_id", sa.Integer(), nullable=False),
        sa.Column("task_item_id", sa.Integer(), nullable=False),
        sa.Column("linked_by", sa.Integer(), nullable=True),
        sa.Column("linked_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.ForeignKeyConstraint(["page_id"], ["wiki_pages.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["task_item_id"], ["task_list_items.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["linked_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("page_id", "task_item_id"),
    )
    op.create_index("ix_wiki_page_task_items_page_id", "wiki_page_task_items", ["page_id"])
    op.create_index("ix_wiki_page_task_items_task_item_id", "wiki_page_task_items", ["task_item_id"])

    # wiki_page_tasks（補助紐づけ：タスク削除後も保持）
    op.create_table(
        "wiki_page_tasks",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("page_id", sa.Integer(), nullable=False),
        sa.Column("task_id", sa.Integer(), nullable=True),          # SET NULL
        sa.Column("task_title", sa.String(500), nullable=False),    # スナップショット
        sa.Column("linked_by", sa.Integer(), nullable=True),
        sa.Column("linked_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.ForeignKeyConstraint(["page_id"], ["wiki_pages.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["task_id"], ["tasks.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["linked_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_wiki_page_tasks_page_id", "wiki_page_tasks", ["page_id"])
    op.create_index("ix_wiki_page_tasks_task_id", "wiki_page_tasks", ["task_id"])
    # task_id が NULL でない場合の UNIQUE 制約（部分インデックス）
    op.execute(
        "CREATE UNIQUE INDEX ix_wiki_page_tasks_unique "
        "ON wiki_page_tasks (page_id, task_id) WHERE task_id IS NOT NULL"
    )


def downgrade():
    op.execute("DROP INDEX IF EXISTS ix_wiki_page_tasks_unique")
    op.drop_table("wiki_page_tasks")
    op.drop_table("wiki_page_task_items")
```

---

## 5. API 設計

### 5.1 エンドポイント一覧

| メソッド | パス | 説明 | 権限 |
|---------|------|------|------|
| GET | `/api/wiki/pages/{id}/task-links` | ページの紐づけタスク一覧取得 | 認証必須 |
| PUT | `/api/wiki/pages/{id}/task-links` | タスクリストアイテム紐づけ一括更新 | 認証必須 |
| POST | `/api/wiki/pages/{id}/task-links/tasks/{task_id}` | 実行中タスク紐づけ追加 | 認証必須 |
| DELETE | `/api/wiki/pages/{id}/task-links/tasks/{task_id}` | 実行中タスク紐づけ解除 | 認証必須 |

### 5.2 GET `/api/wiki/pages/{id}/task-links`

ページに紐づくタスクリストアイテムおよび実行中タスクの一覧を取得する。

**レスポンス**: `200 OK` - `WikiTaskLinksResponse`

```json
{
  "task_items": [
    {
      "id": 1,
      "title": "ログイン機能実装",
      "status": "in_progress",
      "assignee_id": 3,
      "assignee_name": "山田太郎",
      "backlog_ticket_id": "WHT-123",
      "scheduled_date": "2026-03-01",
      "linked_at": "2026-02-25T10:00:00+09:00"
    }
  ],
  "tasks": [
    {
      "link_id": 10,
      "task_id": 42,
      "title": "ログイン画面の修正",
      "status": "in_progress",
      "user_id": 1,
      "display_name": "鈴木花子",
      "backlog_ticket_id": "WHT-124",
      "is_completed": false,
      "linked_at": "2026-02-25T11:00:00+09:00"
    },
    {
      "link_id": 11,
      "task_id": null,
      "title": "DB設計レビュー",
      "status": null,
      "user_id": null,
      "display_name": null,
      "backlog_ticket_id": null,
      "is_completed": true,
      "linked_at": "2026-02-20T09:00:00+09:00"
    }
  ]
}
```

### 5.3 PUT `/api/wiki/pages/{id}/task-links`

タスクリストアイテムの紐づけを一括更新する（差分更新: 追加 + 削除）。

**リクエストボディ**: `WikiTaskItemLinksUpdate`

| フィールド | 型 | 必須 | 説明 |
|------------|-----|------|------|
| task_item_ids | integer[] | Yes | 紐づけるtask_list_item IDリスト（全量指定） |

**レスポンス**: `200 OK` - `WikiTaskLinksResponse`

**動作**: 現在の紐づけと `task_item_ids` の差分を計算し、追加・削除を実行する。

### 5.4 POST `/api/wiki/pages/{id}/task-links/tasks/{task_id}`

実行中タスク（tasks テーブル）を紐づける。

**レスポンス**: `200 OK` - `{"detail": "Linked"}`
**エラー**: `404 Not Found` - ページまたはタスク不存在

### 5.5 DELETE `/api/wiki/pages/{id}/task-links/tasks/{task_id}`

実行中タスクの紐づけを解除する。

**レスポンス**: `204 No Content`
**エラー**: `404 Not Found` - 紐づけ不存在

---

## 6. スキーマ定義

```python
# app/schemas/wiki.py（追記）

from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime, date


class LinkedTaskItemResponse(BaseModel):
    id: int
    title: str
    status: str
    assignee_id: Optional[int]
    assignee_name: Optional[str]
    backlog_ticket_id: Optional[str]
    scheduled_date: Optional[date]
    linked_at: datetime

    class Config:
        from_attributes = True


class LinkedTaskResponse(BaseModel):
    link_id: int                       # wiki_page_tasks.id
    task_id: Optional[int]             # NULL = タスク完了済み
    title: str                         # task_title スナップショット（task 削除後も参照可）
    status: Optional[str]              # NULL = タスク完了済み
    user_id: Optional[int]
    display_name: Optional[str]
    backlog_ticket_id: Optional[str]
    is_completed: bool                 # task_id が NULL の場合 True
    linked_at: datetime

    class Config:
        from_attributes = True


class WikiTaskLinksResponse(BaseModel):
    task_items: List[LinkedTaskItemResponse]
    tasks: List[LinkedTaskResponse]


class WikiTaskItemLinksUpdate(BaseModel):
    task_item_ids: List[int]
```

---

## 7. CRUD 実装

```python
# app/crud/wiki_task_link.py

from typing import List, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import select, delete, insert
from app.models.wiki_task_link import wiki_page_task_items, WikiPageTask
from app.models.task_list_item import TaskListItem
from app.models.task import Task
from app.models.user import User


def get_task_links(db: Session, page_id: int) -> Tuple[list, list]:
    """ページの紐づけタスク一覧を取得（task_items, tasks）。"""
    # task_list_items（task_list_items 削除時は CASCADE で消えるため INNER JOIN）
    task_items_rows = db.execute(
        select(
            TaskListItem.id,
            TaskListItem.title,
            TaskListItem.status,
            TaskListItem.assignee_id,
            User.display_name.label("assignee_name"),
            TaskListItem.backlog_ticket_id,
            TaskListItem.scheduled_date,
            wiki_page_task_items.c.linked_at,
        )
        .join(wiki_page_task_items, TaskListItem.id == wiki_page_task_items.c.task_item_id)
        .outerjoin(User, TaskListItem.assignee_id == User.id)
        .where(wiki_page_task_items.c.page_id == page_id)
        .order_by(wiki_page_task_items.c.linked_at.desc())
    ).fetchall()

    # tasks（task が削除されても wiki_page_tasks レコードは残るため OUTER JOIN）
    tasks_rows = db.execute(
        select(
            WikiPageTask.id.label("link_id"),
            WikiPageTask.task_id,
            WikiPageTask.task_title,
            Task.status,
            Task.user_id,
            User.display_name,
            Task.backlog_ticket_id,
            WikiPageTask.linked_at,
        )
        .where(WikiPageTask.page_id == page_id)
        .outerjoin(Task, WikiPageTask.task_id == Task.id)
        .outerjoin(User, Task.user_id == User.id)
        .order_by(WikiPageTask.linked_at.desc())
    ).fetchall()

    return task_items_rows, tasks_rows


def update_task_item_links(db: Session, page_id: int, task_item_ids: List[int], linked_by: int) -> None:
    """タスクリストアイテム紐づけを一括更新（差分更新）。"""
    # 現在の紐づけを取得
    current = set(
        row[0]
        for row in db.execute(
            select(wiki_page_task_items.c.task_item_id)
            .where(wiki_page_task_items.c.page_id == page_id)
        ).fetchall()
    )
    new_set = set(task_item_ids)

    # 削除
    to_remove = current - new_set
    if to_remove:
        db.execute(
            delete(wiki_page_task_items).where(
                wiki_page_task_items.c.page_id == page_id,
                wiki_page_task_items.c.task_item_id.in_(to_remove),
            )
        )

    # 追加
    to_add = new_set - current
    if to_add:
        db.execute(
            insert(wiki_page_task_items).values(
                [
                    {"page_id": page_id, "task_item_id": tid, "linked_by": linked_by}
                    for tid in to_add
                ]
            )
        )


def add_task_link(db: Session, page_id: int, task_id: int, linked_by: int) -> bool:
    """実行中タスクを紐づける。既に紐づけ済みの場合は True を返す。"""
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        return False
    existing = db.query(WikiPageTask).filter(
        WikiPageTask.page_id == page_id,
        WikiPageTask.task_id == task_id,
    ).first()
    if existing:
        return True
    link = WikiPageTask(
        page_id=page_id,
        task_id=task_id,
        task_title=task.title,  # スナップショット記録
        linked_by=linked_by,
    )
    db.add(link)
    return False


def remove_task_link(db: Session, page_id: int, task_id: int) -> bool:
    """実行中タスクの紐づけを解除する（link_id で削除）。"""
    link = db.query(WikiPageTask).filter(
        WikiPageTask.page_id == page_id,
        WikiPageTask.task_id == task_id,
    ).first()
    if not link:
        return False
    db.delete(link)
    return True
```

---

## 8. フロントエンド UI 設計

### 8.1 ページ詳細画面の「関連タスク」セクション

ページ右サイドバーまたはページ下部に表示するタスクリンクパネル。

```html
<!-- wiki ページ詳細の関連タスクパネル -->
<div id="wiki-task-links-panel" class="card mt-3">
  <div class="card-header d-flex justify-content-between align-items-center">
    <span><i class="bi bi-link-45deg"></i> 関連タスク</span>
    <button class="btn btn-sm btn-outline-primary" id="btn-manage-task-links">
      <i class="bi bi-pencil"></i> 編集
    </button>
  </div>
  <div class="card-body p-2">
    <!-- タスクリストアイテム -->
    <div id="linked-task-items-list">
      <!-- JS で動的生成 -->
    </div>
    <!-- 実行中タスク -->
    <div id="linked-tasks-list" class="mt-2">
      <!-- JS で動的生成 -->
    </div>
    <div id="no-task-links" class="text-muted small text-center py-2" style="display:none">
      関連タスクなし
    </div>
  </div>
</div>
```

### 8.2 タスクリストアイテム検索・紐づけモーダル

```html
<div class="modal fade" id="taskLinksModal" tabindex="-1">
  <div class="modal-dialog modal-lg">
    <div class="modal-content">
      <div class="modal-header">
        <h5 class="modal-title">関連タスクを管理</h5>
        <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
      </div>
      <div class="modal-body">
        <!-- 検索 -->
        <div class="mb-3">
          <input type="text" class="form-control" id="task-item-search"
                 placeholder="タスク名・チケット番号で検索...">
        </div>
        <!-- 検索結果 -->
        <div id="task-item-search-results" class="list-group mb-3" style="max-height:200px; overflow-y:auto">
          <!-- JS で動的生成 -->
        </div>
        <!-- 現在の紐づけ -->
        <h6>紐づけ済みタスク <span class="badge bg-secondary" id="linked-count">0</span></h6>
        <div id="linked-task-items-edit" class="d-flex flex-wrap gap-2">
          <!-- JS でバッジ生成 -->
        </div>
      </div>
      <div class="modal-footer">
        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">キャンセル</button>
        <button type="button" class="btn btn-primary" id="btn-save-task-links">保存</button>
      </div>
    </div>
  </div>
</div>
```

### 8.3 JavaScript (wiki_task_links.js)

```javascript
// static/js/wiki_task_links.js

const pageId = parseInt(document.getElementById("wiki-page-id").dataset.id);
let selectedTaskItemIds = new Set();

// 関連タスク一覧を読み込み
async function loadTaskLinks() {
  const res = await fetch(`/api/wiki/pages/${pageId}/task-links`);
  if (!res.ok) return;
  const data = await res.json();
  renderTaskItems(data.task_items);
  renderActiveTasks(data.tasks);
  selectedTaskItemIds = new Set(data.task_items.map(t => t.id));
  document.getElementById("linked-count").textContent = selectedTaskItemIds.size;
  const noLinks = data.task_items.length === 0 && data.tasks.length === 0;
  document.getElementById("no-task-links").style.display = noLinks ? "" : "none";
}

function renderTaskItems(items) {
  const el = document.getElementById("linked-task-items-list");
  el.innerHTML = items.length === 0 ? "" : `
    <div class="small text-muted mb-1">タスクリスト</div>
    ${items.map(item => `
      <div class="d-flex align-items-center gap-2 mb-1">
        <span class="badge ${statusBadgeClass(item.status)}">${item.status}</span>
        <span class="small">${escapeHtml(item.title)}</span>
        ${item.backlog_ticket_id
          ? `<span class="badge bg-light text-dark border">${escapeHtml(item.backlog_ticket_id)}</span>`
          : ""}
        ${item.assignee_name
          ? `<span class="small text-muted">${escapeHtml(item.assignee_name)}</span>`
          : ""}
      </div>
    `).join("")}
  `;
}

function renderActiveTasks(tasks) {
  const el = document.getElementById("linked-tasks-list");
  if (tasks.length === 0) { el.innerHTML = ""; return; }
  el.innerHTML = `
    <div class="small text-muted mb-1 mt-2">関連タスク</div>
    ${tasks.map(task => `
      <div class="d-flex align-items-center gap-2 mb-1 ${task.is_completed ? "opacity-50" : ""}">
        ${task.is_completed
          ? `<span class="badge bg-success">完了済</span>`
          : `<span class="badge bg-warning text-dark">進行中</span>`}
        <span class="small ${task.is_completed ? "text-decoration-line-through" : ""}">${escapeHtml(task.title)}</span>
        ${task.backlog_ticket_id
          ? `<span class="badge bg-light text-dark border">${escapeHtml(task.backlog_ticket_id)}</span>`
          : ""}
        ${task.display_name
          ? `<span class="small text-muted">${escapeHtml(task.display_name)}</span>`
          : ""}
      </div>
    `).join("")}
  `;
}

function statusBadgeClass(status) {
  return {
    open: "bg-secondary",
    in_progress: "bg-primary",
    done: "bg-success",
  }[status] || "bg-secondary";
}

// モーダル: タスクアイテム検索
let searchTimer = null;
document.getElementById("task-item-search").addEventListener("input", e => {
  clearTimeout(searchTimer);
  searchTimer = setTimeout(() => searchTaskItems(e.target.value), 300);
});

async function searchTaskItems(q) {
  if (!q.trim()) {
    document.getElementById("task-item-search-results").innerHTML = "";
    return;
  }
  const res = await fetch(`/api/task-list/all?status=open&status=in_progress&q=${encodeURIComponent(q)}`);
  if (!res.ok) return;
  const items = await res.json();
  const el = document.getElementById("task-item-search-results");
  el.innerHTML = items.slice(0, 20).map(item => `
    <button type="button"
      class="list-group-item list-group-item-action d-flex justify-content-between align-items-center ${selectedTaskItemIds.has(item.id) ? "active" : ""}"
      data-id="${item.id}"
      data-title="${escapeHtml(item.title)}"
      onclick="toggleTaskItemLink(this, ${item.id}, '${escapeHtml(item.title)}')">
      <span>${escapeHtml(item.title)}</span>
      ${item.backlog_ticket_id ? `<span class="badge bg-light text-dark border ms-2">${escapeHtml(item.backlog_ticket_id)}</span>` : ""}
    </button>
  `).join("") || '<div class="list-group-item text-muted">該当なし</div>';
}

function toggleTaskItemLink(el, id, title) {
  if (selectedTaskItemIds.has(id)) {
    selectedTaskItemIds.delete(id);
    el.classList.remove("active");
    document.querySelector(`#linked-task-items-edit [data-id="${id}"]`)?.remove();
  } else {
    selectedTaskItemIds.add(id);
    el.classList.add("active");
    addLinkedBadge(id, title);
  }
  document.getElementById("linked-count").textContent = selectedTaskItemIds.size;
}

function addLinkedBadge(id, title) {
  const el = document.getElementById("linked-task-items-edit");
  const badge = document.createElement("span");
  badge.className = "badge bg-primary d-flex align-items-center gap-1";
  badge.dataset.id = id;
  badge.innerHTML = `${escapeHtml(title)} <button type="button" class="btn-close btn-close-white btn-sm" onclick="toggleTaskItemLink(null, ${id}, '')"></button>`;
  el.appendChild(badge);
}

// 保存
document.getElementById("btn-save-task-links").addEventListener("click", async () => {
  const res = await fetch(`/api/wiki/pages/${pageId}/task-links`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ task_item_ids: [...selectedTaskItemIds] }),
  });
  if (res.ok) {
    bootstrap.Modal.getInstance(document.getElementById("taskLinksModal")).hide();
    loadTaskLinks();
    showToast("関連タスクを更新しました", "success");
  }
});

// 初期読み込み
loadTaskLinks();
```

---

## 9. 技術的注意事項

### 9.1 tasks テーブルのライフサイクル

`tasks` テーブルの行は `done` 操作で物理削除される。`wiki_page_tasks` の `task_id` には `ON DELETE SET NULL` を設定しているため、タスク削除後も紐づけレコードは保持される。`task_title` スナップショットにより、UI では「完了済みタスク名」として表示継続できる。

UI での表示例:
- `task_id` が NULL でない場合: 通常の進行中タスクとして表示
- `task_id` が NULL の場合: 取り消し線 + 「完了済み」バッジで表示

### 9.2 task_list_items との紐づけが主体

`wiki_page_task_items`（task_list_items との紐づけ）を主要な永続紐づけとして位置付ける。タスクリストアイテムはバックログとして永続するため、長期間にわたる関連付けに適している。

### 9.3 N+1 クエリ回避

`get_task_links()` では JOIN を使用して1クエリで取得する。ページ詳細の表示時は遅延ロードではなく明示的なクエリを使用すること。

### 9.4 将来拡張（Phase 2 以降）

- `wiki_page_task_items` に `note` カラムを追加（紐づけコメント）
- 逆引き: タスクリストアイテム詳細から「関連WIKI」を表示
- アクティビティログ: 紐づけ変更の履歴記録

---

## 10. 技術的負債

| 項目 | 内容 | 優先度 |
|------|------|--------|
| task_list_items 検索の `q` パラメータ | 現在の `/api/task-list/all` にはキーワード検索パラメータがない（ISSUE1.md #ISSUE-1-02 参照） | 中 |
| 逆引き機能 | タスクリストアイテム側から関連 WIKI ページを参照する機能未実装 | 低 |
