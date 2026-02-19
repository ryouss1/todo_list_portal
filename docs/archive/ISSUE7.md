# ISSUE7: ISSUE6 再発防止策 + 重複登録防止の未実装調査

## ステータス: **主要対策完了** ✅（一部ドキュメント系は未着手）

| 対応項目 | 優先度 | ステータス |
|---------|--------|-----------|
| DB レベル重複チェック導入（4.1） | P1 | ✅ 完了 |
| ステータス自動リセット実装（4.2） | P1 | ✅ 完了 |
| 共通 create_and_start 関数（5.2） | P1 | ✅ 完了 |
| フロントエンド二重クリック防止（4.3） | P2 | ✅ 完了 |
| テスト追加: クロスエンドポイント + Done後再Start（5.1） | P2 | ✅ 完了（8件追加） |
| Unassign 制限実装（3.4） | P3 | ✅ 完了 |
| 仕様書の事後条件追加（5.3） | P2 | ⬜ 未着手 |
| コードレビューチェックリスト策定（5.4） | P3 | ⬜ 未着手 |

**実施日**: 2026-02-16

## 1. 背景

ISSUE6（Task List の Start 後に Task Timer に表示されない）の修正を踏まえ、以下を調査・検討する。

1. **再発防止策**: 同様の不具合を今後発生させないための対策
2. **重複登録防止の未実装**: 仕様に定義されているが実装されていない機能の洗い出し

---

## 2. ISSUE6 の根本原因分析

### 2.1 なぜバグが混入したか

| 原因カテゴリ | 詳細 |
|-------------|------|
| **仕様の不整合** | SPEC 概要に「タイマー付き Task にコピー」と記載しているが、詳細フロー（4.4節 Step 1-6）にタイマー作成ステップが**欠落** |
| **既存ロジックの未再利用** | `task_service.start_timer()` / `crud_task.start_timer()` が既にあるのに、`task_list_service.start_as_task()` は `Task` を直接 `db.add()` しタイマーロジックを省略 |
| **テスト不足** | Start 後に「Task の status が in_progress」「TaskTimeEntry が存在する」を検証するテストが無かった |
| **クロスモジュール検証の欠如** | `POST /api/task-list/{id}/start` の結果を `GET /api/tasks/` で確認する統合テストが無かった |

### 2.2 コードの問題パターン

```
task_list_service.py が直接 Task モデルを生成
    ↓
task_service / crud_task の "start" ロジックをバイパス
    ↓
タイマー開始・ステータス設定が漏れる
```

本来あるべき姿:
```
task_list_service.py → task_service.create_and_start_task() を呼ぶ
    ↓
Task 作成 + タイマー開始が1箇所で管理される（DRY 原則）
```

---

## 3. 仕様 vs 実装のギャップ一覧

調査の結果、SPEC に定義されているが**未実装の機能**が複数発見された。

### 3.1 Start の重複チェック（SPEC 4.4 Step 3 / 7.4） ✅ 修正済み

**仕様**: 同一 `source_item_id` を持つ Task が DB に存在する場合、Start をブロック（400）

```
チェック対象: db.query(Task).filter(Task.source_item_id == item.id).first()
```

**実装**: `item.status != "open"` のみチェック（ステータスベース）

**問題点**:
- `crud/task.py` に `count_by_source_item_id()` が実装済みだが**未使用**（デッドコード）
- ステータスチェックはアプリレベルのみで、DB レベルの UNIQUE 制約なし
- TOCTOU 競合（2つの同時リクエストが両方 `status == "open"` を読んで通過する可能性）

### 3.2 ステータス自動リセット（SPEC 7.6 / tasks SPEC Step 9） ✅ 修正済み

**仕様**: Task Done 時に、リンクされた全 Task が 0 件になったら `TaskListItem.status` を `in_progress` → `open` に自動リセット

**実装**: **完全未実装**

**問題点**:
- `done_task()` は `total_seconds` の蓄積のみ行い、ステータスリセットしない
- `batch_done()` も同様
- `delete_task()` は `source_item` に一切触れない
- 結果: **Start した TaskListItem は永久に `in_progress` のまま** → 再 Start 不可能

### 3.3 担当者チェック（SPEC 4.4 Step 2）

**仕様**: Start は `assignee_id` が現在のユーザーであることを確認（403）

**実装**: `_get_visible_item()` による可視性チェックのみ。未割当アイテムの Start も許可（自動割当で対処）

**差異レベル**: 低（仕様を拡張する形で実装。自動割当は利便性向上）

### 3.4 Unassign 制限（SPEC 7.3） ✅ 修正済み

**仕様**: `status` が `in_progress` のアイテムはアサイン解除不可（403）

**実装**: **未実装** — `in_progress` でも Unassign 可能

### 3.5 フロントエンド二重クリック防止 ✅ 修正済み

**仕様**: 暗黙（UI 品質）

**実装**: **未実装** — `startAsTask()` にボタン無効化・デバウンスなし。高速ダブルクリックで2リクエスト送信の可能性

---

## 4. 重複登録防止の修正方針

### 4.1 DB レベルチェック導入（推奨）

`start_as_task()` でステータスチェックに加え、DB レベルの重複チェックを追加:

```python
# app/services/task_list_service.py
from app.crud import task as crud_task

def start_as_task(db, item_id, user_id):
    item = _get_visible_item(db, item_id, user_id)
    if item.status != "open":
        raise ConflictError("Item is already started")

    # DB レベル重複チェック（SPEC 7.4 準拠）
    if crud_task.count_by_source_item_id(db, item.id) > 0:
        raise ConflictError("A task for this item already exists")
    ...
```

### 4.2 ステータス自動リセット実装（推奨）

`done_task()` / `batch_done()` / `delete_task()` で、リンク先 TaskListItem のステータスを同期:

```python
# app/services/task_service.py — done_task / delete_task 内
if source_item_id:
    remaining = crud_task.count_by_source_item_id(db, source_item_id)
    if remaining == 0:
        source_item = crud_tli.get_item(db, source_item_id)
        if source_item and source_item.status == "in_progress":
            source_item.status = "open"
```

### 4.3 フロントエンド二重クリック防止

```javascript
async function startAsTask(id) {
    const btn = document.querySelector(`[onclick="startAsTask(${id})"]`);
    if (btn) btn.disabled = true;
    try {
        await api.post(`/api/task-list/${id}/start`);
        window.location.href = '/tasks';
    } catch (e) {
        if (btn) btn.disabled = false;
        showToast(e.message, 'danger');
    }
}
```

---

## 5. 再発防止策

### 5.1 テスト改善

| 対策 | 説明 | 優先度 |
|------|------|--------|
| **クロスエンドポイント統合テスト** | Service A で作成したリソースが Service B の API で正しく見えることを検証 | 高 |
| **"Start" 契約テスト** | 「Start = status:in_progress + TaskTimeEntry(stopped_at=None)」を共通アサーションで検証 | 高 |
| **ネガティブテスト強化** | Done 後の再 Start、Delete 後の再 Start、二重クリックシミュレーション | 中 |
| **仕様準拠チェックテスト** | SPEC の各ステップに対応するテストの有無を確認するチェックリスト | 中 |

**具体例: クロスエンドポイント統合テスト**
```python
def test_start_task_visible_in_tasks_api_with_timer(client):
    """Start → GET /api/tasks/ で in_progress + タイマー稼働中を確認"""
    res = client.post("/api/task-list/", json={"title": "Cross Check"})
    item_id = res.json()["id"]

    res = client.post(f"/api/task-list/{item_id}/start")
    task_id = res.json()["id"]

    # Tasks API で確認
    res = client.get("/api/tasks/")
    task = next(t for t in res.json() if t["id"] == task_id)
    assert task["status"] == "in_progress"

    # タイマー確認
    res = client.get(f"/api/tasks/{task_id}/time-entries")
    entries = res.json()
    assert len(entries) == 1
    assert entries[0]["stopped_at"] is None
```

**具体例: Done 後の再 Start テスト**
```python
def test_start_after_done_reopens_item(client, db_session):
    """Done → TaskListItem.status が open に戻り → 再 Start 可能"""
    res = client.post("/api/task-list/", json={"title": "Restart Test"})
    item_id = res.json()["id"]

    # Start → Done
    res = client.post(f"/api/task-list/{item_id}/start")
    task_id = res.json()["id"]
    client.post(f"/api/tasks/{task_id}/done")

    # Item が open に戻ること
    res = client.get(f"/api/task-list/{item_id}")
    assert res.json()["status"] == "open"

    # 再 Start 可能
    res = client.post(f"/api/task-list/{item_id}/start")
    assert res.status_code == 200
```

### 5.2 アーキテクチャ改善

| 対策 | 説明 | 優先度 |
|------|------|--------|
| **共通 create_and_start 関数** | `task_service` に Task 作成+タイマー開始を一括で行う関数を追加し、`task_list_service` から呼ぶ | 高 |
| **クロスモジュール直接モデル操作の禁止** | `task_list_service` が `Task`/`TaskTimeEntry` を直接生成せず、`task_service` 経由にする | 高 |
| **デッドコードの除去 or 活用** | `count_by_source_item_id` を実際に使用するか削除 | 中 |

**共通関数の例**:
```python
# app/services/task_service.py
def create_and_start_task(db, user_id, title, description=None,
                          category_id=None, backlog_ticket_id=None,
                          source_item_id=None) -> Task:
    """Task 作成 + タイマー即時開始（start_as_task 用）"""
    task = Task(
        user_id=user_id, title=title, description=description,
        category_id=category_id, backlog_ticket_id=backlog_ticket_id,
        source_item_id=source_item_id, status="in_progress",
    )
    db.add(task)
    db.flush()
    entry = TaskTimeEntry(task_id=task.id, started_at=datetime.now(timezone.utc))
    db.add(entry)
    return task
```

### 5.3 仕様書改善

| 対策 | 説明 | 優先度 |
|------|------|--------|
| **事後条件の明記** | 各 API エンドポイントに「事後条件（Post-conditions）」セクションを追加 | 高 |
| **概要と詳細フローの整合性チェック** | 概要で「タイマー付き」と書くなら、詳細フローにもタイマー作成ステップを含める | 高 |
| **テスト仕様との対応表** | SPEC の各ステップに対応するテストケース名を明記 | 中 |

**事後条件の例**:
```markdown
### POST /api/task-list/{id}/start — 事後条件
1. Task が `status=in_progress` で作成されている
2. TaskTimeEntry が `stopped_at=NULL` で作成されている（タイマー稼働中）
3. TaskListItem の `status` が `in_progress` に変更されている
4. TaskListItem の `assignee_id` が設定されている（未割当だった場合は自動設定）
```

### 5.4 コードレビューチェックリスト

| チェック項目 | 説明 |
|------------|------|
| **既存ロジックの再利用** | 新機能実装時、同等の処理が既に存在しないか確認。存在する場合は呼び出しで対応 |
| **クロスモジュール操作** | 他モジュールのモデルを直接操作する場合、そのモジュールのドメイン不変条件を確認 |
| **仕様の全ステップ実装確認** | SPEC の処理フロー各ステップが実装に反映されているか1:1で確認 |
| **ステータス遷移の完全性** | ステータスを変更する処理がある場合、逆方向の遷移（リセット）も実装されているか確認 |
| **デッドコードの検出** | 仕様のために用意された関数が実際に使われているか確認 |

### 5.5 フロントエンド品質

| 対策 | 説明 | 優先度 |
|------|------|--------|
| **ボタン二重クリック防止** | 非同期処理中はボタンを `disabled` に設定 | 中 |
| **楽観的 UI 更新** | Start 後は即座にボタンを非表示にし、API 結果を待たない | 低 |

---

## 6. 対応優先度まとめ

| 優先度 | 対応項目 | 工数目安 | ステータス |
|--------|---------|---------|-----------|
| **P1（高）** | DB レベル重複チェック導入（4.1） | 小 | ✅ 完了 |
| **P1（高）** | ステータス自動リセット実装（4.2） | 中 | ✅ 完了 |
| **P1（高）** | 共通 create_and_start 関数（5.2） | 中 | ✅ 完了 |
| **P2（中）** | フロントエンド二重クリック防止（4.3） | 小 | ✅ 完了 |
| **P2（中）** | 仕様書の事後条件追加（5.3） | 小 | ⬜ 未着手 |
| **P2（中）** | テスト追加: クロスエンドポイント + Done後再Start（5.1） | 中 | ✅ 完了 |
| **P3（低）** | Unassign 制限実装（3.4） | 小 | ✅ 完了 |
| **P3（低）** | コードレビューチェックリスト策定（5.4） | 小 | ⬜ 未着手 |

---

## 7. 技術的負債

| 項目 | 状態 | 影響 |
|------|------|------|
| `crud_task.count_by_source_item_id()` が未使用 | **解消** — DB重複チェック・ステータス同期で活用 | — |
| TaskListItem のステータス自動リセット未実装 | **解消** — `_sync_source_item_status()` で実装 | — |
| `tasks.source_item_id` に UNIQUE 制約なし | 設計判断 | 仕様上は1:1だが DB では1:N 許容（DB重複チェックで制御） |
| `task_list_service` が Task ドメインのモデルを直接操作 | **解消** — `svc_task.create_and_start_task()` に移譲 | — |

---

## 8. 対応完了記録

**実施日**: 2026-02-16

### 8.1 実装した修正

| 対応項目 | 修正ファイル | 内容 |
|---------|-------------|------|
| DB レベル重複チェック | `task_list_service.py` | `crud_task.count_by_source_item_id()` による重複防止 |
| ステータス自動リセット | `task_service.py` | `_sync_source_item_status()` — done/batch_done/delete 時に source item を open に戻す |
| 共通 create_and_start 関数 | `task_service.py` | `create_and_start_task()` — Task作成+タイマー開始を一括管理 |
| start_as_task リファクタ | `task_list_service.py` | 直接モデル操作を排除、`svc_task.create_and_start_task()` に移譲 |
| Unassign 制限 | `task_list_service.py` | `in_progress` アイテムの unassign を 403 でブロック |
| 二重クリック防止 | `task_list.js` | Start ボタンの disabled 制御 |
| キャッシュバスト | `task_list.html` | v4 → v5 |

### 8.2 追加テスト（8件）

| テスト名 | 検証内容 |
|---------|---------|
| `test_done_resets_item_status_to_open` | Done → item が open に戻る |
| `test_done_restart_after_done` | Done → 再 Start 可能 |
| `test_delete_task_resets_item_status` | Delete → item が open に戻る |
| `test_batch_done_resets_item_status` | Batch-Done → item が open に戻る |
| `test_done_does_not_reset_done_status` | 手動 done のアイテムはリセット対象外 |
| `test_start_with_existing_task_returns_conflict` | DB レベル重複チェック |
| `test_unassign_in_progress_forbidden` | in_progress の unassign は 403 |
| `test_unassign_open_allowed` | open の unassign は正常（リグレッション） |

### 8.3 テスト結果

- `tests/test_task_list.py`: 35件全パス（既存27 + 新規8）
- `tests/test_tasks.py`: 32件全パス（リグレッションなし）
- `tests/test_authorization.py` + `tests/test_presence.py`: 29件全パス
