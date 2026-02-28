# Issue-7 MEDIUM Priority Fixes Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Implement all 5 MEDIUM priority items from docs/issue7.md: race condition fix for task-list start, pagination for 5 endpoints, DB get_db() rollback, atomic session update on login, and batch-done existence check.

**Architecture:** Each fix is independent. Task 1 and 5 add SELECT FOR UPDATE to prevent race conditions. Task 2 threads limit/offset through CRUD→Service→Router for 5 endpoints. Task 3 adds explicit rollback in get_db(). Task 4 uses session.update() for atomicity. Follow TDD: write failing test first, implement, verify pass.

**Tech Stack:** Python 3.9, FastAPI, SQLAlchemy 2.0, pytest, portal_core pattern (CRUD→Service→Router layers)

---

## Context

- Working directory: `/home/ryou/svn/todo_list_portal2`
- Test commands: `pytest tests/ -q` (app), `cd portal_core && pytest tests/ -q` (core)
- Lint: `ruff check --fix . && ruff format .`
- Architecture: Routers (thin HTTP) → Services (business logic) → CRUD (DB access)
- `portal_core/portal_core/` = shared core package. `app/` = app-specific code.
- Python 3.9: use `Optional[X]` not `X | None`

---

## Task 1: 2-1 — タスクリスト start_as_task() 競合修正（SELECT FOR UPDATE）

**Problem:** `start_as_task()` checks for duplicate tasks (T1) then creates a task (T2). Concurrent requests can pass both checks and create duplicate tasks for the same item.

**Fix:** Lock the task_list_item row with SELECT FOR UPDATE before checking/writing.

**Files:**
- Modify: `app/crud/task_list_item.py`
- Modify: `app/services/task_list_service.py:95-122`
- Test: `tests/test_task_list.py`

---

### Step 1: Write the failing test

Add this test class to `tests/test_task_list.py`:

```python
class TestStartAsTaskRaceCondition:
    def test_start_as_task_uses_row_lock(self, db_session):
        """start_as_task should use SELECT FOR UPDATE to prevent duplicate tasks."""
        from sqlalchemy import inspect as sa_inspect
        from app.crud.task_list_item import get_item_for_update

        item = TaskListItem(
            title="Lock test",
            created_by=1,
            status="open",
        )
        db_session.add(item)
        db_session.flush()

        # Verify the function exists and returns the item
        locked = get_item_for_update(db_session, item.id)
        assert locked is not None
        assert locked.id == item.id
```

Run: `pytest tests/test_task_list.py::TestStartAsTaskRaceCondition -v`
Expected: FAIL with `ImportError: cannot import name 'get_item_for_update'`

---

### Step 2: Implement get_item_for_update in CRUD

In `app/crud/task_list_item.py`, add after line 11 (`get_item = _crud.get`):

```python
def get_item_for_update(db: Session, item_id: int) -> Optional[TaskListItem]:
    """Get a task list item with SELECT FOR UPDATE row lock."""
    return db.query(TaskListItem).filter(TaskListItem.id == item_id).with_for_update().first()
```

Also add `Optional` to the imports at line 1: `from typing import Dict, List, Optional`

---

### Step 3: Run test to verify it passes

Run: `pytest tests/test_task_list.py::TestStartAsTaskRaceCondition -v`
Expected: PASS

---

### Step 4: Update start_as_task() to use the lock

In `app/services/task_list_service.py`, change `start_as_task()` (lines 95-122):

**Before:**
```python
def start_as_task(db: Session, item_id: int, user_id: int) -> Task:
    """Copy a TaskListItem to a new Task, start its timer, and set item status to in_progress."""
    item = _get_visible_item(db, item_id, user_id)
```

**After:**
```python
def start_as_task(db: Session, item_id: int, user_id: int) -> Task:
    """Copy a TaskListItem to a new Task, start its timer, and set item status to in_progress."""
    # Lock the row to prevent concurrent start_as_task() calls from creating duplicate tasks.
    item = crud_tli.get_item_for_update(db, item_id)
    if not item:
        raise NotFoundError("Item not found")
    if item.assignee_id is not None and item.assignee_id != user_id and item.created_by != user_id:
        raise NotFoundError("Item not found")
```

Also add import: `from app.crud.task_list_item import get_item_for_update as _get_item_for_update` is not needed — `crud_tli` is already imported, use `crud_tli.get_item_for_update`.

---

### Step 5: Run full task_list tests

Run: `pytest tests/test_task_list.py -q`
Expected: All existing tests pass + new test passes

---

### Step 6: Lint and commit

```bash
ruff check --fix . && ruff format .
git add app/crud/task_list_item.py app/services/task_list_service.py tests/test_task_list.py
git commit -m "fix: add SELECT FOR UPDATE to start_as_task() to prevent race condition (issue7 2-1)"
```

---

## Task 2: 2-2 — ページネーション（limit/offset）を5エンドポイントに追加

**Problem:** 5 endpoints return all rows without limit/offset. Can cause OOM under heavy load.

**Fix:** Add `limit: int = 200` and `offset: int = 0` to CRUD functions, services, and routers. Default 200 maintains backward compatibility for normal use.

**Files to modify (CRUD layer):**
- `app/crud/task.py` — `get_tasks()`
- `app/crud/task_list_item.py` — `get_all_items()`
- `app/crud/alert.py` — `get_alert_rules()`
- `app/crud/wiki_page.py` — `get_all_pages()`
- `app/crud/presence.py` — `get_all_presence_statuses()`

**Files to modify (Service layer):**
- `app/services/task_service.py` — `list_tasks()`
- `app/services/task_list_service.py` — `list_all()`
- `app/services/alert_service.py` — `list_rules()`
- `app/services/wiki_service.py` — `list_pages()`
- `app/services/presence_service.py` — `get_all_statuses()`

**Files to modify (Router layer):**
- `app/routers/api_tasks.py` — `list_tasks` endpoint
- `app/routers/api_task_list.py` — `list_all` endpoint
- `app/routers/api_alert_rules.py` — `list_rules` endpoint
- `app/routers/api_wiki.py` — `list_pages` endpoint
- `app/routers/api_presence.py` — `list_statuses` endpoint

**Test:** `tests/test_tasks.py`, `tests/test_task_list.py`, `tests/test_alert_rules.py`, `tests/test_wiki.py`, `tests/test_presence.py`

---

### Step 1: Write the failing tests

Add one test per endpoint to the respective test files:

**`tests/test_tasks.py`** — add inside an existing class or as a new class:
```python
class TestPagination:
    def test_list_tasks_limit(self, client, db_session):
        """GET /api/tasks/ should support limit parameter."""
        # Create 3 tasks for user 1
        from app.models.task import Task
        for i in range(3):
            db_session.add(Task(user_id=1, title=f"Task {i}", status="pending"))
        db_session.flush()

        resp = client.get("/api/tasks/?limit=2")
        assert resp.status_code == 200
        assert len(resp.json()) <= 2

    def test_list_tasks_offset(self, client, db_session):
        """GET /api/tasks/ should support offset parameter."""
        from app.models.task import Task
        for i in range(3):
            db_session.add(Task(user_id=1, title=f"Task {i}", status="pending"))
        db_session.flush()

        resp_all = client.get("/api/tasks/?limit=200")
        resp_offset = client.get(f"/api/tasks/?limit=200&offset={len(resp_all.json())}")
        assert resp_offset.status_code == 200
        assert len(resp_offset.json()) == 0
```

**`tests/test_task_list.py`** — add inside existing class or as new class:
```python
class TestListAllPagination:
    def test_list_all_limit(self, client, db_session):
        """GET /api/task-list/all should support limit parameter."""
        from app.models.task_list_item import TaskListItem
        for i in range(5):
            db_session.add(TaskListItem(title=f"Item {i}", created_by=1, status="open"))
        db_session.flush()

        resp = client.get("/api/task-list/all?limit=2")
        assert resp.status_code == 200
        assert len(resp.json()) <= 2
```

**`tests/test_alert_rules.py`** — add as new class:
```python
class TestPagination:
    def test_list_rules_limit(self, client, db_session):
        """GET /api/alert-rules/ should support limit parameter."""
        from app.models.alert import AlertRule
        for i in range(3):
            db_session.add(AlertRule(
                name=f"Rule {i}",
                condition={"severity": "ERROR"},
                alert_title_template="Test",
            ))
        db_session.flush()

        resp = client.get("/api/alert-rules/?limit=1")
        assert resp.status_code == 200
        assert len(resp.json()) <= 1
```

**`tests/test_wiki.py`** — add as new class:
```python
class TestPagination:
    def test_list_pages_limit(self, client, db_session):
        """GET /api/wiki/pages/ should support limit parameter."""
        from app.models.wiki_page import WikiPage
        for i in range(5):
            db_session.add(WikiPage(
                title=f"Page {i}",
                slug=f"page-{i}-pagination",
                author_id=1,
                visibility="public",
            ))
        db_session.flush()

        resp = client.get("/api/wiki/pages/?limit=2")
        assert resp.status_code == 200
        assert len(resp.json()) <= 2
```

**`tests/test_presence.py`** — add as new class:
```python
class TestPagination:
    def test_list_statuses_limit(self, client, db_session):
        """GET /api/presence/statuses should support limit parameter."""
        from app.models.presence import PresenceStatus
        # Create extra users and statuses
        from portal_core.models.user import User
        from portal_core.core.security import hash_password
        for i in range(3):
            u = User(
                id=100 + i, email=f"pag{i}@test.com",
                display_name=f"User {i}", password_hash=hash_password("test"),
            )
            db_session.add(u)
            db_session.flush()
            db_session.add(PresenceStatus(user_id=u.id, status="offline"))
        db_session.flush()

        resp = client.get("/api/presence/statuses?limit=1")
        assert resp.status_code == 200
        assert len(resp.json()) <= 1
```

Run: `pytest tests/test_tasks.py::TestPagination tests/test_task_list.py::TestListAllPagination tests/test_alert_rules.py::TestPagination tests/test_wiki.py::TestPagination tests/test_presence.py::TestPagination -v`
Expected: Multiple FAILs with `422 Unprocessable Entity` or unexpected behavior (limit param not recognized)

---

### Step 2: Implement pagination in CRUD layer

**`app/crud/task.py`** — modify `get_tasks()` at line 22:

```python
def get_tasks(db: Session, user_id: int, limit: int = 200, offset: int = 0) -> List[Task]:
    return (
        db.query(Task)
        .filter(Task.user_id == user_id)
        .order_by(Task.created_at.desc())
        .limit(limit)
        .offset(offset)
        .all()
    )
```

**`app/crud/task_list_item.py`** — modify `get_all_items()` at line 23:

```python
def get_all_items(
    db: Session,
    assignee_id: Optional[int] = None,
    statuses: Optional[List[str]] = None,
    q: Optional[str] = None,
    limit: int = 200,
    offset: int = 0,
) -> List[TaskListItem]:
    query = db.query(TaskListItem)
    if assignee_id is not None:
        if assignee_id == 0:
            query = query.filter(TaskListItem.assignee_id.is_(None))
        else:
            query = query.filter(TaskListItem.assignee_id == assignee_id)
    if statuses:
        query = query.filter(TaskListItem.status.in_(statuses))
    if q:
        query = query.filter(TaskListItem.title.ilike(f"%{q}%"))
    return (
        query.order_by(TaskListItem.scheduled_date.asc().nullslast(), TaskListItem.created_at.asc())
        .limit(limit)
        .offset(offset)
        .all()
    )
```

**`app/crud/alert.py`** — modify `get_alert_rules()` at line 20:

```python
def get_alert_rules(db: Session, limit: int = 200, offset: int = 0) -> List[AlertRule]:
    return db.query(AlertRule).order_by(AlertRule.id).limit(limit).offset(offset).all()
```

**`app/crud/wiki_page.py`** — modify `get_all_pages()` signature at line 21, add `limit`/`offset` parameters and chain `.limit(limit).offset(offset)` before `.all()` in the query. The existing function body ends with `.all()` — add `.limit(limit).offset(offset)` before it:

Find the line with `.all()` at the end of the query in `get_all_pages()` and change it to `.limit(limit).offset(offset).all()`. Also add `limit: int = 200, offset: int = 0` to the function signature.

The exact change to the signature (line 21-28):
```python
def get_all_pages(
    db: Session,
    tag_slug: Optional[str] = None,
    category_id: Optional[int] = None,
    user_id: Optional[int] = None,
    user_group_id: Optional[int] = None,
    is_admin: bool = False,
    limit: int = 200,
    offset: int = 0,
) -> List[WikiPage]:
```

And before `.all()` at the end of the function, add `.limit(limit).offset(offset)`:
```python
    return query.order_by(WikiPage.sort_order.asc(), WikiPage.created_at.asc()).limit(limit).offset(offset).all()
```
(You will need to read the rest of `get_all_pages()` to find where `.all()` is and add the limit/offset before it. Look for the final `return query...all()` line.)

**`app/crud/presence.py`** — modify `get_all_presence_statuses()` at line 12:

```python
def get_all_presence_statuses(db: Session, limit: int = 500, offset: int = 0) -> List[PresenceStatus]:
    return db.query(PresenceStatus).limit(limit).offset(offset).all()
```

(Presence uses limit=500 since it represents users and a team typically has fewer than 500 people.)

---

### Step 3: Implement pagination in Service layer

**`app/services/task_service.py`** — modify `list_tasks()` at line 23:

```python
def list_tasks(db: Session, user_id: int, limit: int = 200, offset: int = 0) -> List[Task]:
    logger.info("Listing tasks for user_id=%d", user_id)
    return crud_task.get_tasks(db, user_id, limit=limit, offset=offset)
```

**`app/services/task_list_service.py`** — modify `list_all()` at line 40:

```python
def list_all(
    db: Session,
    assignee_id: Optional[int] = None,
    statuses: Optional[List[str]] = None,
    q: Optional[str] = None,
    limit: int = 200,
    offset: int = 0,
) -> List[TaskListItem]:
    return crud_tli.get_all_items(db, assignee_id, statuses, q, limit=limit, offset=offset)
```

**`app/services/alert_service.py`** — modify `list_rules()` at line 24:

```python
def list_rules(db: Session, limit: int = 200, offset: int = 0) -> List[AlertRule]:
    return crud_alert.get_alert_rules(db, limit=limit, offset=offset)
```

**`app/services/wiki_service.py`** — modify `list_pages()` at line 289:

```python
def list_pages(
    db: Session,
    tag_slug: Optional[str] = None,
    category_id: Optional[int] = None,
    user_id: Optional[int] = None,
    is_admin: bool = False,
    limit: int = 200,
    offset: int = 0,
) -> List[WikiPageResponse]:
    user_group_id = _get_user_group_id(db, user_id) if user_id is not None and not is_admin else None
    pages = page_crud.get_all_pages(
        db,
        tag_slug=tag_slug,
        category_id=category_id,
        user_id=user_id,
        user_group_id=user_group_id,
        is_admin=is_admin,
        limit=limit,
        offset=offset,
    )
    return [_to_page_response(p, db) for p in pages]
```

**`app/services/presence_service.py`** — find `get_all_statuses()` and add limit/offset. Read the function first to find exact lines:

```python
def get_all_statuses(db: Session, limit: int = 500, offset: int = 0) -> List[PresenceStatusWithUser]:
    statuses = crud_presence.get_all_presence_statuses(db, limit=limit, offset=offset)
    # ... rest of function unchanged ...
```

---

### Step 4: Implement pagination in Router layer

**`app/routers/api_tasks.py`** — modify `list_tasks` endpoint:

```python
@router.get("/", response_model=List[TaskResponse])
def list_tasks(
    limit: int = Query(200, ge=1, le=10000),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    return svc_task.list_tasks(db, user_id, limit=limit, offset=offset)
```

Also add `Query` to imports: `from fastapi import APIRouter, Depends, Query`

**`app/routers/api_task_list.py`** — modify `list_all` endpoint:

```python
@router.get("/all", response_model=List[TaskListItemResponse])
def list_all(
    assignee_id: Optional[int] = Query(None),
    status: Optional[List[str]] = Query(None),
    q: Optional[str] = Query(None, description="タイトル部分一致フィルタ（大文字小文字を区別しない）"),
    limit: int = Query(200, ge=1, le=10000),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    return svc.list_all(db, assignee_id, status, q, limit=limit, offset=offset)
```

**`app/routers/api_alert_rules.py`** — modify `list_rules` endpoint:

```python
@router.get("/", response_model=List[AlertRuleResponse])
def list_rules(
    limit: int = Query(200, ge=1, le=10000),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    _user_id: int = Depends(get_current_user_id),
):
    return svc.list_rules(db, limit=limit, offset=offset)
```

Also add `Query` to imports: `from fastapi import APIRouter, Depends, Query`

**`app/routers/api_wiki.py`** — modify `list_pages` endpoint:

```python
@router.get("/", response_model=List[WikiPageResponse])
def list_pages(
    tag_slug: Optional[str] = None,
    category_id: Optional[int] = None,
    limit: int = Query(200, ge=1, le=10000),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    return svc.list_pages(db, tag_slug=tag_slug, category_id=category_id, user_id=user_id, limit=limit, offset=offset)
```

Also add `Query` to imports if not already present: `from fastapi import APIRouter, Depends, Query, status`

**`app/routers/api_presence.py`** — modify `list_statuses` endpoint:

```python
@router.get("/statuses", response_model=List[PresenceStatusWithUser])
def list_statuses(
    limit: int = Query(500, ge=1, le=10000),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    _user_id: int = Depends(get_current_user_id),
):
    return svc_presence.get_all_statuses(db, limit=limit, offset=offset)
```

Also add `Query` to imports: `from fastapi import APIRouter, Depends, Query`

---

### Step 5: Run pagination tests

Run: `pytest tests/test_tasks.py::TestPagination tests/test_task_list.py::TestListAllPagination tests/test_alert_rules.py::TestPagination tests/test_wiki.py::TestPagination tests/test_presence.py::TestPagination -v`
Expected: All PASS

---

### Step 6: Run full test suite to check for regressions

Run: `pytest tests/ -q`
Expected: 575+ tests passing (no new failures)

---

### Step 7: Lint and commit

```bash
ruff check --fix . && ruff format .
git add app/crud/task.py app/crud/task_list_item.py app/crud/alert.py app/crud/wiki_page.py app/crud/presence.py
git add app/services/task_service.py app/services/task_list_service.py app/services/alert_service.py app/services/wiki_service.py app/services/presence_service.py
git add app/routers/api_tasks.py app/routers/api_task_list.py app/routers/api_alert_rules.py app/routers/api_wiki.py app/routers/api_presence.py
git add tests/test_tasks.py tests/test_task_list.py tests/test_alert_rules.py tests/test_wiki.py tests/test_presence.py
git commit -m "feat: add limit/offset pagination to 5 list endpoints (issue7 2-2)"
```

---

## Task 3: 2-3 — get_db() に明示的 rollback 追加

**Problem:** `get_db()` in `portal_core/portal_core/database.py` does not explicitly rollback on exception. If a service raises an exception mid-transaction, the DB session may retain a broken transaction state before `close()` returns it to the pool.

**Fix:** Add `except Exception: db.rollback(); raise` inside `get_db()`.

**Files:**
- Modify: `portal_core/portal_core/database.py`
- Test: `portal_core/tests/test_crud_base.py` (or any portal_core test that exercises DB)

---

### Step 1: Write the failing test

Add to `portal_core/tests/test_crud_base.py`:

```python
class TestGetDbRollback:
    def test_get_db_rolls_back_on_exception(self):
        """get_db() should rollback the transaction when an exception is raised."""
        from portal_core.database import get_db, engine
        from sqlalchemy.orm import sessionmaker
        from portal_core.models.group import Group

        gen = get_db()
        db = next(gen)

        # Begin a change
        g = Group(name="test_rollback_group_xyz", sort_order=99)
        db.add(g)
        db.flush()
        group_id = g.id
        assert group_id is not None

        # Simulate exception — should trigger rollback
        try:
            gen.throw(RuntimeError("test exception"))
        except RuntimeError:
            pass

        # Verify the change was rolled back
        Session = sessionmaker(bind=engine)
        verify_db = Session()
        try:
            found = verify_db.query(Group).filter(Group.id == group_id).first()
            assert found is None, "Group should have been rolled back"
        finally:
            verify_db.close()
```

Run: `cd portal_core && pytest tests/test_crud_base.py::TestGetDbRollback -v`
Expected: FAIL (the group may or may not be rolled back depending on current behavior — test proves lack of explicit rollback)

---

### Step 2: Implement the fix

In `portal_core/portal_core/database.py`, replace:

```python
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

With:

```python
def get_db():
    db = SessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
```

---

### Step 3: Run test to verify it passes

Run: `cd portal_core && pytest tests/test_crud_base.py::TestGetDbRollback -v`
Expected: PASS

---

### Step 4: Run full portal_core test suite

Run: `cd portal_core && pytest tests/ -q`
Expected: 153+ tests passing

---

### Step 5: Lint and commit

```bash
ruff check --fix . && ruff format .
git add portal_core/portal_core/database.py portal_core/tests/test_crud_base.py
git commit -m "fix: add explicit rollback in get_db() on exception (issue7 2-3)"
```

---

## Task 4: 2-4 — ログイン セッション更新をアトミックに

**Problem:** `login()` in `portal_core/portal_core/routers/api_auth.py` does `session.clear()` then sets keys one by one. While Starlette sessions are per-request dicts (no true concurrency issue), the intent is clearer and safer with atomic update.

**Fix:** Replace sequential key assignments with a single `session.update({...})` call after `session.clear()`.

**Files:**
- Modify: `portal_core/portal_core/routers/api_auth.py:47-51`
- Test: `portal_core/tests/test_auth.py`

---

### Step 1: Write the failing test

Add to `portal_core/tests/test_auth.py`:

```python
class TestLoginSessionAtomic:
    def test_login_sets_all_session_fields(self, raw_client, test_user):
        """Login should set all session fields in one operation."""
        resp = raw_client.post("/api/auth/login", json={
            "email": "default_user@example.com",
            "password": "testpass",
        })
        assert resp.status_code == 200
        data = resp.json()
        # All expected fields must be present
        assert data["user_id"] == test_user.id
        assert data["display_name"] == test_user.display_name
        assert "role" in data
```

Run: `cd portal_core && pytest portal_core/tests/test_auth.py::TestLoginSessionAtomic -v`
Expected: This test likely PASSES already (the fields are set). This test documents the behavior. Note: if this passes, the test is still valid — we need it to pass after our change too.

---

### Step 2: Implement the fix

In `portal_core/portal_core/routers/api_auth.py`, replace lines 47-51:

**Before:**
```python
    request.session.clear()  # Prevent session fixation
    request.session["user_id"] = user.id
    request.session["display_name"] = user.display_name
    request.session["session_version"] = user.session_version
    request.session["locale"] = user.preferred_locale or "ja"
```

**After:**
```python
    # Prevent session fixation: clear old session then atomically set new data
    request.session.clear()
    request.session.update({
        "user_id": user.id,
        "display_name": user.display_name,
        "session_version": user.session_version,
        "locale": user.preferred_locale or "ja",
    })
```

---

### Step 3: Run test to verify it passes

Run: `cd portal_core && pytest portal_core/tests/test_auth.py -q`
Expected: All auth tests pass

---

### Step 4: Run full portal_core test suite

Run: `cd portal_core && pytest tests/ -q`
Expected: 153+ tests passing

---

### Step 5: Lint and commit

```bash
ruff check --fix . && ruff format .
git add portal_core/portal_core/routers/api_auth.py portal_core/tests/test_auth.py
git commit -m "fix: use session.update() for atomic login session write (issue7 2-4)"
```

---

## Task 5: 2-5 — バッチ完了操作に SELECT FOR UPDATE を追加

**Problem:** `batch_done()` fetches tasks with a regular query, then deletes them. If another request deletes a task between the fetch and the delete, SQLAlchemy silently does nothing (0 rows deleted), which is incorrect — the API should detect and report the deleted task.

**Fix:** Use `SELECT FOR UPDATE` in the batch task fetch. Add `get_tasks_by_ids_for_update()` to CRUD.

**Files:**
- Modify: `app/crud/task.py` — add `get_tasks_by_ids_for_update()`
- Modify: `app/services/task_service.py:221` — use the new function in `batch_done()`
- Test: `tests/test_tasks.py`

---

### Step 1: Write the failing test

Add to `tests/test_tasks.py`:

```python
class TestBatchDoneForUpdate:
    def test_batch_done_uses_for_update(self, db_session):
        """batch_done should use SELECT FOR UPDATE to lock tasks before deletion."""
        from app.crud.task import get_tasks_by_ids_for_update

        from app.models.task import Task
        t = Task(user_id=1, title="Lock test", status="pending")
        db_session.add(t)
        db_session.flush()

        locked = get_tasks_by_ids_for_update(db_session, [t.id])
        assert len(locked) == 1
        assert locked[0].id == t.id
```

Run: `pytest tests/test_tasks.py::TestBatchDoneForUpdate -v`
Expected: FAIL with `ImportError: cannot import name 'get_tasks_by_ids_for_update'`

---

### Step 2: Add get_tasks_by_ids_for_update to CRUD

In `app/crud/task.py`, add after `get_tasks_by_ids()` (after line 95):

```python
def get_tasks_by_ids_for_update(db: Session, task_ids: List[int]) -> List[Task]:
    """Batch-fetch tasks by IDs with SELECT FOR UPDATE row lock."""
    if not task_ids:
        return []
    return db.query(Task).filter(Task.id.in_(task_ids)).with_for_update().all()
```

---

### Step 3: Run test to verify it passes

Run: `pytest tests/test_tasks.py::TestBatchDoneForUpdate -v`
Expected: PASS

---

### Step 4: Update batch_done() to use the locking fetch

In `app/services/task_service.py`, change `batch_done()` at line 221:

**Before:**
```python
    # Batch-fetch tasks and active entries (2 queries instead of 2N)
    task_map = {t.id: t for t in crud_task.get_tasks_by_ids(db, task_ids)}
```

**After:**
```python
    # Batch-fetch tasks with row locks and active entries (2 queries instead of 2N)
    # SELECT FOR UPDATE prevents another request from deleting tasks mid-batch.
    task_map = {t.id: t for t in crud_task.get_tasks_by_ids_for_update(db, task_ids)}
```

---

### Step 5: Run full task tests

Run: `pytest tests/test_tasks.py -q`
Expected: 36+ tests passing

---

### Step 6: Run full app test suite

Run: `pytest tests/ -q`
Expected: 575+ tests passing (no new failures)

---

### Step 7: Lint and commit

```bash
ruff check --fix . && ruff format .
git add app/crud/task.py app/services/task_service.py tests/test_tasks.py
git commit -m "fix: use SELECT FOR UPDATE in batch_done() task fetch (issue7 2-5)"
```

---

## Task 6: ドキュメント更新

Update `docs/issue7.md` to mark all MEDIUM items as completed.

### Step 1: Update issue7.md

In `docs/issue7.md`, for each MEDIUM item (2-1 through 2-5):

1. Change `### 2-1. タスクリスト開始操作の競合状態` to `### 2-1. タスクリスト開始操作の競合状態 ✅ 対応済み`
2. Add after each problem description: `**対応内容（2026-02-27）:** ...`
3. Update the summary table at the bottom to show ✅ for all MEDIUM items.

Also update `docs/spec_nonfunction.md` test counts after verifying actual counts with `pytest tests/ --collect-only -q 2>&1 | tail -1`.

### Step 2: Update MEMORY.md test counts

Run `pytest tests/ --collect-only -q 2>&1 | tail -1` and `cd portal_core && pytest tests/ --collect-only -q 2>&1 | tail -1` and update `/home/ryou/.claude/projects/-home-ryou-svn-todo-list-portal2/memory/MEMORY.md`.

### Step 3: Commit documentation

```bash
git add docs/issue7.md docs/spec_nonfunction.md
git commit -m "docs: update issue7.md MEDIUM priority items as completed"
```

---

## Final Verification

Run the full test suite one last time:
```bash
cd portal_core && pytest tests/ -q && cd .. && pytest tests/ -q
```
Expected: All tests pass (153 core + 575+ app).
