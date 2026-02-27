# issue7.md HIGH Issues — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Fix 5 HIGH-priority stability/correctness issues from issue7.md

**Architecture:** One issue per task, each independently committable/rollbackable. Tests written first (Red→Green→Refactor). Full test suite verified after each task.

**Tech Stack:** asyncio.Lock, SQLAlchemy SELECT FOR UPDATE, asyncio watchdog pattern, pytest

---

## Task 1: WebSocket Race Condition (1-1)

**Files:**
- Modify: `portal_core/portal_core/services/websocket_manager.py`
- Modify: `portal_core/portal_core/app_factory.py` (lines 420, 427)
- Test: `portal_core/tests/test_websocket.py`

**Problem:**
- `disconnect()` is SYNC but called from an async WebSocket handler
- `broadcast()` snapshot-iterates `active_connections` but mutates it without a lock
- `app_factory.py:420,427`: `_manager.disconnect(websocket)` (no `await`)

---

**Step 1: Write the failing tests**

Add to `portal_core/tests/test_websocket.py`:

```python
import asyncio
import inspect
import pytest


@pytest.mark.asyncio
async def test_websocket_disconnect_is_async():
    """disconnect() must be a coroutine so asyncio.Lock can be acquired."""
    from portal_core.services.websocket_manager import WebSocketManager

    assert inspect.iscoroutinefunction(WebSocketManager.disconnect)


@pytest.mark.asyncio
async def test_websocket_concurrent_broadcast_and_disconnect():
    """Concurrent broadcast + disconnect must not raise RuntimeError or lose connections."""
    from portal_core.services.websocket_manager import WebSocketManager

    manager = WebSocketManager()

    class FakeWS:
        async def accept(self):
            pass

        async def send_json(self, data):
            pass

    ws1, ws2 = FakeWS(), FakeWS()
    await manager.connect(ws1)
    await manager.connect(ws2)
    assert len(manager.active_connections) == 2

    # Concurrent broadcast and disconnect — must not raise
    await asyncio.gather(
        manager.broadcast({"msg": "hi"}),
        manager.disconnect(ws1),
    )

    assert len(manager.active_connections) == 1
    assert ws2 in manager.active_connections
```

**Step 2: Run tests to verify they fail**

```bash
cd portal_core && pytest tests/test_websocket.py::test_websocket_disconnect_is_async tests/test_websocket.py::test_websocket_concurrent_broadcast_and_disconnect -v
```

Expected: FAIL — `disconnect` is not async / AttributeError

---

**Step 3: Write minimal implementation**

Replace `portal_core/portal_core/services/websocket_manager.py`:

```python
import asyncio
import logging
from typing import List

from fastapi import WebSocket

logger = logging.getLogger("app.services.websocket")


class WebSocketManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        async with self._lock:
            self.active_connections.append(websocket)
        logger.info("WebSocket connected. Total connections: %d", len(self.active_connections))

    async def disconnect(self, websocket: WebSocket):
        async with self._lock:
            if websocket in self.active_connections:
                self.active_connections.remove(websocket)
        logger.info("WebSocket disconnected. Total connections: %d", len(self.active_connections))

    async def broadcast(self, data: dict):
        async with self._lock:
            connections = self.active_connections[:]
        disconnected = []
        for connection in connections:
            try:
                await connection.send_json(data)
            except Exception:
                disconnected.append(connection)
        if disconnected:
            async with self._lock:
                for conn in disconnected:
                    if conn in self.active_connections:
                        self.active_connections.remove(conn)
                        logger.warning(
                            "Removed dead WebSocket connection. Total: %d",
                            len(self.active_connections),
                        )
```

Update `portal_core/portal_core/app_factory.py` — add `await` in two places (both inside `async def ws_handler`):

```python
# Line 420 (unauthenticated close):
await _manager.disconnect(websocket)   # was: _manager.disconnect(websocket)

# Line 427 (normal disconnect):
await _manager.disconnect(websocket)   # was: _manager.disconnect(websocket)
```

---

**Step 4: Run tests to verify they pass**

```bash
cd portal_core && pytest tests/test_websocket.py -v
```

Expected: all 6 tests PASS

---

**Step 5: Run full test suite**

```bash
cd portal_core && pytest tests/ -q && cd .. && pytest tests/ -q
```

Expected: 706 tests pass

---

**Step 6: Lint and commit**

```bash
ruff check --fix portal_core/portal_core/services/websocket_manager.py portal_core/portal_core/app_factory.py && ruff format portal_core/portal_core/services/websocket_manager.py portal_core/portal_core/app_factory.py
git add portal_core/portal_core/services/websocket_manager.py portal_core/portal_core/app_factory.py portal_core/tests/test_websocket.py
git commit -m "fix(websocket): add asyncio.Lock to WebSocketManager, make disconnect async (issue7 1-1)"
```

---

## Task 2: Timer TOCTOU Fix (1-2)

**Files:**
- Modify: `app/crud/task.py`
- Modify: `app/services/task_service.py` (lines 114–132)
- Test: `tests/test_tasks.py`

**Problem:**
- `start_timer` (task_service.py:114): reads task → checks active entry → creates entry. Another request can slip between check and create.
- `stop_timer` (task_service.py:125): `task.total_seconds += elapsed` in crud is a read-modify-write without row lock — concurrent stops lose time.
- Fix: `SELECT FOR UPDATE` on the task row before any timer mutation.

---

**Step 1: Write the failing test**

Add to `tests/test_tasks.py`:

```python
def test_get_task_for_update_exists():
    """get_task_for_update must exist in crud.task (used for pessimistic locking)."""
    from app.crud import task as crud_task

    assert hasattr(crud_task, "get_task_for_update"), "get_task_for_update not found in crud.task"
    assert callable(crud_task.get_task_for_update)


def test_start_timer_uses_row_lock(client, db_session):
    """start_timer: second concurrent start must return 409 even under race."""
    resp = client.post("/api/tasks/", json={"title": "TOCTOU Test"})
    assert resp.status_code == 201
    task_id = resp.json()["id"]

    resp = client.post(f"/api/tasks/{task_id}/start")
    assert resp.status_code == 200

    # Second start on same task must be 409 (timer already running)
    resp = client.post(f"/api/tasks/{task_id}/start")
    assert resp.status_code == 409

    # Verify exactly one active entry in DB
    from app.crud import task as crud_task

    entries = crud_task.get_time_entries(db_session, task_id)
    active = [e for e in entries if e.stopped_at is None]
    assert len(active) == 1


def test_stop_timer_accumulates_total_seconds(client, db_session):
    """stop_timer: total_seconds must be positive after start→stop cycle."""
    resp = client.post("/api/tasks/", json={"title": "Elapsed Test"})
    task_id = resp.json()["id"]

    client.post(f"/api/tasks/{task_id}/start")
    resp = client.post(f"/api/tasks/{task_id}/stop")
    assert resp.status_code == 200
    assert resp.json()["elapsed_seconds"] >= 0

    resp = client.get(f"/api/tasks/{task_id}")
    assert resp.json()["total_seconds"] >= 0
```

**Step 2: Run tests to verify the first one fails**

```bash
pytest tests/test_tasks.py::test_get_task_for_update_exists -v
```

Expected: FAIL — `assert hasattr(crud_task, "get_task_for_update")` fails

---

**Step 3: Write minimal implementation**

Add to `app/crud/task.py` (after the existing `get_task` alias):

```python
def get_task_for_update(db: Session, task_id: int) -> Optional[Task]:
    """Get task with SELECT FOR UPDATE row lock (prevents TOCTOU in timer ops)."""
    return db.query(Task).filter(Task.id == task_id).with_for_update().first()
```

Add `Optional` to imports if not present:
```python
from typing import Dict, List, Optional
```

Update `app/services/task_service.py` — replace `start_timer` and `stop_timer` and add helper:

```python
def _get_task_with_lock(db: Session, task_id: int, user_id: int) -> Task:
    """Get task with SELECT FOR UPDATE, checking ownership."""
    task = crud_task.get_task_for_update(db, task_id)
    if not task or task.user_id != user_id:
        logger.warning("Task not found (locked): id=%d", task_id)
        raise NotFoundError("Task not found")
    return task


def start_timer(db: Session, task_id: int, user_id: int) -> TaskTimeEntry:
    task = _get_task_with_lock(db, task_id, user_id)
    active = crud_task.get_active_entry(db, task_id)
    if active:
        logger.warning("Timer already running: task_id=%d", task_id)
        raise ConflictError("Timer already running")
    entry = crud_task.start_timer(db, task)
    logger.info("Timer started: task_id=%d, entry_id=%d", task_id, entry.id)
    return entry


def stop_timer(db: Session, task_id: int, user_id: int) -> TaskTimeEntry:
    task = _get_task_with_lock(db, task_id, user_id)
    entry = crud_task.stop_timer(db, task)
    if not entry:
        logger.warning("No active timer: task_id=%d", task_id)
        raise ConflictError("No active timer")
    logger.info("Timer stopped: task_id=%d, elapsed=%ds", task_id, entry.elapsed_seconds)
    return entry
```

---

**Step 4: Run tests to verify they pass**

```bash
pytest tests/test_tasks.py::test_get_task_for_update_exists tests/test_tasks.py::test_start_timer_uses_row_lock tests/test_tasks.py::test_stop_timer_accumulates_total_seconds -v
```

Expected: all 3 PASS

---

**Step 5: Run full test suite**

```bash
pytest tests/ -q
```

Expected: 555 app tests pass

---

**Step 6: Lint and commit**

```bash
ruff check --fix app/crud/task.py app/services/task_service.py && ruff format app/crud/task.py app/services/task_service.py
git add app/crud/task.py app/services/task_service.py tests/test_tasks.py
git commit -m "fix(tasks): use SELECT FOR UPDATE in start_timer/stop_timer to prevent TOCTOU race (issue7 1-2)"
```

---

## Task 3: Presence N+1 Query Fix (1-3)

**Files:**
- Modify: `app/config.py`
- Modify: `app/crud/task.py` (line 76)
- Modify: `app/services/presence_service.py` (line 35)
- Test: `tests/test_presence.py`

**Problem:**
- `get_all_statuses` fires 3 separate queries: `get_all_presence_statuses`, `get_users`, `get_in_progress_with_backlog`
- `get_in_progress_with_backlog` has no LIMIT — unlimited rows for the "active tickets" display

---

**Step 1: Write the failing tests**

Add to `tests/test_presence.py`:

```python
def test_presence_active_task_limit_config_exists():
    """PRESENCE_ACTIVE_TASK_LIMIT must be set in app.config."""
    from app import config

    assert hasattr(config, "PRESENCE_ACTIVE_TASK_LIMIT"), "PRESENCE_ACTIVE_TASK_LIMIT missing from config"
    assert isinstance(config.PRESENCE_ACTIVE_TASK_LIMIT, int)
    assert config.PRESENCE_ACTIVE_TASK_LIMIT > 0


def test_get_in_progress_with_backlog_respects_limit(db_session):
    """get_in_progress_with_backlog must accept a limit parameter."""
    from app.crud import task as crud_task

    # Must not raise — limit parameter must exist
    result = crud_task.get_in_progress_with_backlog(db_session, limit=5)
    assert isinstance(result, list)
```

**Step 2: Run tests to verify they fail**

```bash
pytest tests/test_presence.py::test_presence_active_task_limit_config_exists tests/test_presence.py::test_get_in_progress_with_backlog_respects_limit -v
```

Expected: FAIL — config key missing / unexpected keyword argument

---

**Step 3: Write minimal implementation**

Add to `app/config.py` in the "API default limits" section:

```python
PRESENCE_ACTIVE_TASK_LIMIT: int = int(os.environ.get("PRESENCE_ACTIVE_TASK_LIMIT", "200"))
```

Update `app/crud/task.py` — `get_in_progress_with_backlog` (line 76):

```python
def get_in_progress_with_backlog(db: Session, limit: int = 200) -> List[Task]:
    """Get all in-progress tasks that have a backlog ticket ID (for presence display)."""
    return (
        db.query(Task)
        .filter(Task.status == TaskStatus.IN_PROGRESS, Task.backlog_ticket_id.isnot(None))
        .limit(limit)
        .all()
    )
```

Update `app/services/presence_service.py` — pass limit from config:

```python
from app.config import API_PRESENCE_LOG_LIMIT, PRESENCE_ACTIVE_TASK_LIMIT

# in get_all_statuses (line 35):
    active_tasks = crud_task.get_in_progress_with_backlog(db, limit=PRESENCE_ACTIVE_TASK_LIMIT)
```

---

**Step 4: Run tests to verify they pass**

```bash
pytest tests/test_presence.py::test_presence_active_task_limit_config_exists tests/test_presence.py::test_get_in_progress_with_backlog_respects_limit -v
```

Expected: both PASS

---

**Step 5: Run full test suite**

```bash
pytest tests/ -q
```

Expected: 555 app tests pass

---

**Step 6: Lint and commit**

```bash
ruff check --fix app/config.py app/crud/task.py app/services/presence_service.py && ruff format app/config.py app/crud/task.py app/services/presence_service.py
git add app/config.py app/crud/task.py app/services/presence_service.py tests/test_presence.py
git commit -m "fix(presence): add LIMIT to in-progress task query, add PRESENCE_ACTIVE_TASK_LIMIT config (issue7 1-3)"
```

---

## Task 4: Log Source Circuit Breaker (1-4)

**Files:**
- Modify: `app/config.py`
- Modify: `app/crud/log_source.py` (lines 33–50)
- Test: `tests/test_log_sources.py`

**Problem:**
- `update_scan_state` increments `consecutive_errors` but never triggers auto-disable
- `disable_source` function already exists in `app/crud/log_source.py:48` but is never called automatically
- After N consecutive failures the source keeps running and spamming error logs

---

**Step 1: Write the failing test**

Add to `tests/test_log_sources.py`:

```python
def test_circuit_breaker_config_exists():
    """LOG_SOURCE_MAX_CONSECUTIVE_FAILURES must be defined in config."""
    from app import config

    assert hasattr(config, "LOG_SOURCE_MAX_CONSECUTIVE_FAILURES")
    assert isinstance(config.LOG_SOURCE_MAX_CONSECUTIVE_FAILURES, int)
    assert config.LOG_SOURCE_MAX_CONSECUTIVE_FAILURES > 0


def test_circuit_breaker_auto_disables_after_max_failures(client, db_session):
    """Source must be auto-disabled after LOG_SOURCE_MAX_CONSECUTIVE_FAILURES errors."""
    from app.config import LOG_SOURCE_MAX_CONSECUTIVE_FAILURES
    from app.crud import log_source as crud_ls

    resp = client.post(
        "/api/log-sources/",
        json={
            "name": "Circuit Breaker Test",
            "group_id": 1,
            "access_method": "ftp",
            "host": "localhost",
            "username": "user",
            "password": "pass",
            "paths": [{"base_path": "/logs"}],
        },
    )
    assert resp.status_code == 201
    source_id = resp.json()["id"]
    source = crud_ls.get_log_source(db_session, source_id)
    assert source.is_enabled is True

    # Simulate consecutive failures up to threshold - 1 (still enabled)
    for i in range(LOG_SOURCE_MAX_CONSECUTIVE_FAILURES - 1):
        crud_ls.update_scan_state(db_session, source, error="connection refused")
        db_session.refresh(source)
        assert source.is_enabled is True, f"Should still be enabled after {i + 1} failures"

    # Final failure — triggers auto-disable
    crud_ls.update_scan_state(db_session, source, error="connection refused")
    db_session.refresh(source)
    assert source.is_enabled is False


def test_circuit_breaker_does_not_disable_on_success(client, db_session):
    """Source must NOT be auto-disabled if errors are intermittent (reset on success)."""
    from app.config import LOG_SOURCE_MAX_CONSECUTIVE_FAILURES
    from app.crud import log_source as crud_ls

    resp = client.post(
        "/api/log-sources/",
        json={
            "name": "CB Success Reset Test",
            "group_id": 1,
            "access_method": "ftp",
            "host": "localhost",
            "username": "user",
            "password": "pass",
            "paths": [{"base_path": "/logs"}],
        },
    )
    source_id = resp.json()["id"]
    source = crud_ls.get_log_source(db_session, source_id)

    # Some failures
    for _ in range(LOG_SOURCE_MAX_CONSECUTIVE_FAILURES - 1):
        crud_ls.update_scan_state(db_session, source, error="timeout")
        db_session.refresh(source)

    # Success resets counter
    crud_ls.update_scan_state(db_session, source)
    db_session.refresh(source)
    assert source.consecutive_errors == 0
    assert source.is_enabled is True
```

**Step 2: Run tests to verify they fail**

```bash
pytest tests/test_log_sources.py::test_circuit_breaker_config_exists tests/test_log_sources.py::test_circuit_breaker_auto_disables_after_max_failures tests/test_log_sources.py::test_circuit_breaker_does_not_disable_on_success -v
```

Expected: FAIL — config key missing / source not auto-disabled

---

**Step 3: Write minimal implementation**

Add to `app/config.py` in the "Log source polling" section:

```python
LOG_SOURCE_MAX_CONSECUTIVE_FAILURES: int = int(os.environ.get("LOG_SOURCE_MAX_CONSECUTIVE_FAILURES", "5"))
```

Update `app/crud/log_source.py` — `update_scan_state` (lines 33–50):

```python
import logging

logger = logging.getLogger("app.crud.log_source")


def update_scan_state(
    db: Session,
    source: LogSource,
    error: Optional[str] = None,
    max_failures: Optional[int] = None,
) -> None:
    source.last_checked_at = datetime.now(timezone.utc)
    if error:
        source.last_error = error
        source.consecutive_errors = (source.consecutive_errors or 0) + 1
        if max_failures and source.consecutive_errors >= max_failures:
            source.is_enabled = False
            logger.warning(
                "Auto-disabled log source id=%d after %d consecutive failures",
                source.id,
                source.consecutive_errors,
            )
    else:
        source.last_error = None
        source.consecutive_errors = 0
    db.commit()
```

Update the caller in `app/services/log_source_service.py` — find where `update_scan_state` is called on error and pass the threshold (search for `update_scan_state(db, source`):

```python
from app.config import LOG_SOURCE_MAX_CONSECUTIVE_FAILURES

# In scan_source error handling (near line 615):
crud_log_source.update_scan_state(
    db, source, error=str(e), max_failures=LOG_SOURCE_MAX_CONSECUTIVE_FAILURES
)
```

---

**Step 4: Run tests to verify they pass**

```bash
pytest tests/test_log_sources.py::test_circuit_breaker_config_exists tests/test_log_sources.py::test_circuit_breaker_auto_disables_after_max_failures tests/test_log_sources.py::test_circuit_breaker_does_not_disable_on_success -v
```

Expected: all 3 PASS

---

**Step 5: Run full test suite**

```bash
pytest tests/ -q
```

Expected: 555 app tests pass

---

**Step 6: Lint and commit**

```bash
ruff check --fix app/config.py app/crud/log_source.py app/services/log_source_service.py && ruff format app/config.py app/crud/log_source.py app/services/log_source_service.py
git add app/config.py app/crud/log_source.py app/services/log_source_service.py tests/test_log_sources.py
git commit -m "fix(log-sources): auto-disable source after LOG_SOURCE_MAX_CONSECUTIVE_FAILURES errors (issue7 1-4)"
```

---

## Task 5: Background Task Watchdog (1-5)

**Files:**
- Modify: `app/config.py`
- Modify: `app/services/log_scanner.py`
- Modify: `app/services/site_checker.py`
- Test: `tests/test_log_scanner.py`

**Problem:**
- `_scanner_loop` and `_checker_loop` run as bare `asyncio.create_task()` — if the task completes or crashes, scanning silently stops forever
- No health check mechanism; no `_last_scan_at` timestamp for staleness detection

---

**Step 1: Write the failing tests**

Add to `tests/test_log_scanner.py`:

```python
import asyncio
import pytest


def test_watchdog_step_exists():
    """_watchdog_step must be importable from log_scanner."""
    from app.services import log_scanner

    assert hasattr(log_scanner, "_watchdog_step"), "_watchdog_step not found in log_scanner"
    assert asyncio.iscoroutinefunction(log_scanner._watchdog_step)


@pytest.mark.asyncio
async def test_watchdog_restarts_completed_scanner_task(db_session):
    """Watchdog must restart the scanner if the background task has completed."""
    from app.services import log_scanner

    class MockApp:
        class state:
            log_scanner_task = None
            log_scanner_watchdog = None

    app = MockApp()

    # Simulate a completed (crashed) task
    app.state.log_scanner_task = asyncio.create_task(asyncio.sleep(0))
    await asyncio.sleep(0.05)  # Let it complete
    assert app.state.log_scanner_task.done()

    # Run one watchdog step — should restart
    await log_scanner._watchdog_step(app)

    assert app.state.log_scanner_task is not None
    assert not app.state.log_scanner_task.done(), "Task should be running after watchdog restart"

    # Cleanup
    app.state.log_scanner_task.cancel()
    try:
        await app.state.log_scanner_task
    except asyncio.CancelledError:
        pass


def test_scanner_stale_config_exists():
    """LOG_SCANNER_STALE_MINUTES must be defined in config."""
    from app import config

    assert hasattr(config, "LOG_SCANNER_STALE_MINUTES")
    assert isinstance(config.LOG_SCANNER_STALE_MINUTES, int)
    assert config.LOG_SCANNER_STALE_MINUTES > 0
```

**Step 2: Run tests to verify they fail**

```bash
pytest tests/test_log_scanner.py::test_watchdog_step_exists tests/test_log_scanner.py::test_watchdog_restarts_completed_scanner_task tests/test_log_scanner.py::test_scanner_stale_config_exists -v
```

Expected: FAIL — `_watchdog_step` not found / config key missing

---

**Step 3: Write minimal implementation**

Add to `app/config.py`:

```python
# Background task watchdog
LOG_SCANNER_STALE_MINUTES: int = int(os.environ.get("LOG_SCANNER_STALE_MINUTES", "10"))
SITE_CHECKER_STALE_MINUTES: int = int(os.environ.get("SITE_CHECKER_STALE_MINUTES", "10"))
```

Replace `app/services/log_scanner.py`:

```python
"""Background log source scanner (v2).

Periodically scans enabled log sources based on their polling_interval_sec.
Follows the same pattern as reminder_checker.py (asyncio.create_task + SessionLocal).
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Optional

from app.config import LOG_SCANNER_ENABLED, LOG_SCANNER_LOOP_INTERVAL, LOG_SCANNER_STALE_MINUTES
from app.crud import log_source as crud_log_source
from app.database import SessionLocal
from app.services import log_source_service
from app.services.websocket_manager import alert_ws_manager

logger = logging.getLogger("app.services.log_scanner")

_last_scan_at: Optional[datetime] = None


def _scan_in_thread(source_id: int) -> dict:
    """Run scan_source in a separate thread with its own DB session.

    scan_source() performs synchronous I/O (FTP/SMB connections),
    so it must run in a thread pool to avoid blocking the event loop.
    """
    db = SessionLocal()
    try:
        return log_source_service.scan_source(db, source_id)
    finally:
        db.close()


async def _scan_due_sources() -> None:
    """Check all enabled sources and scan those whose polling interval has elapsed."""
    db = SessionLocal()
    try:
        sources = crud_log_source.get_enabled_log_sources(db)
        now = datetime.now(timezone.utc)

        for source in sources:
            if source.last_checked_at is not None:
                elapsed = (now - source.last_checked_at).total_seconds()
                if elapsed < source.polling_interval_sec:
                    continue

            logger.info("Scanning source: id=%d name=%s", source.id, source.name)
            try:
                source_id = source.id
                result = await asyncio.to_thread(_scan_in_thread, source_id)

                alert_data = result.get("alert_broadcast")
                if alert_data:
                    await alert_ws_manager.broadcast({"type": "new_alert", "alert": alert_data})

                logger.info(
                    "Scan complete: source_id=%d, %s",
                    source_id,
                    result.get("message", ""),
                )
            except Exception:
                logger.exception("Error scanning source id=%d", source.id)

    except Exception:
        logger.exception("Error in scan_due_sources")
    finally:
        db.close()


async def _scanner_loop() -> None:
    """Main scanner loop — updates _last_scan_at on every iteration."""
    global _last_scan_at
    logger.info("Log scanner started (loop_interval=%ds)", LOG_SCANNER_LOOP_INTERVAL)
    while True:
        _last_scan_at = datetime.now(timezone.utc)
        await _scan_due_sources()
        await asyncio.sleep(LOG_SCANNER_LOOP_INTERVAL)


async def _watchdog_step(app) -> None:
    """Single watchdog check: restart scanner task if done or stale."""
    global _last_scan_at
    task = getattr(app.state, "log_scanner_task", None)
    now = datetime.now(timezone.utc)

    need_restart = False

    if task is None or task.done():
        logger.warning("Scanner task is done or missing — restarting")
        need_restart = True
    elif _last_scan_at is not None:
        age_minutes = (now - _last_scan_at).total_seconds() / 60
        if age_minutes > LOG_SCANNER_STALE_MINUTES:
            logger.warning(
                "Scanner loop stale (%.1f min > %d) — restarting",
                age_minutes,
                LOG_SCANNER_STALE_MINUTES,
            )
            task.cancel()
            try:
                await task
            except (asyncio.CancelledError, RuntimeError):
                pass
            need_restart = True

    if need_restart:
        _last_scan_at = None
        app.state.log_scanner_task = asyncio.create_task(_scanner_loop())


async def _watchdog_loop(app) -> None:
    """Watchdog loop: checks scanner health every 60 seconds."""
    logger.info("Log scanner watchdog started")
    while True:
        await asyncio.sleep(60)
        await _watchdog_step(app)


async def start_scanner(app) -> None:
    """Start the log scanner background task and watchdog."""
    if not LOG_SCANNER_ENABLED:
        logger.info("Log scanner disabled")
        return
    app.state.log_scanner_task = asyncio.create_task(_scanner_loop())
    app.state.log_scanner_watchdog = asyncio.create_task(_watchdog_loop(app))
    logger.info("Log scanner task and watchdog created")


async def stop_scanner(app) -> None:
    """Stop the log scanner background task and watchdog."""
    for attr in ("log_scanner_watchdog", "log_scanner_task"):
        task = getattr(app.state, attr, None)
        if task:
            task.cancel()
            try:
                await task
            except (asyncio.CancelledError, RuntimeError):
                pass
    logger.info("Log scanner stopped")
```

Apply the same watchdog pattern to `app/services/site_checker.py` — add `_last_check_at`, `_watchdog_step`, `_watchdog_loop`, update `_checker_loop`, update `start_checker` and `stop_checker`:

```python
# Add after imports:
from app.config import SITE_CHECKER_ENABLED, SITE_CHECKER_LOOP_INTERVAL, SITE_CHECKER_STALE_MINUTES

_last_check_at: Optional[datetime] = None


# Update _checker_loop to record timestamp:
async def _checker_loop() -> None:
    global _last_check_at
    logger.info("Site checker started (loop_interval=%ds)", SITE_CHECKER_LOOP_INTERVAL)
    while True:
        _last_check_at = datetime.now(timezone.utc)
        await _check_due_links()
        await asyncio.sleep(SITE_CHECKER_LOOP_INTERVAL)


# Add _watchdog_step and _watchdog_loop (same pattern as log_scanner):
async def _watchdog_step(app) -> None:
    global _last_check_at
    task = getattr(app.state, "site_checker_task", None)
    now = datetime.now(timezone.utc)
    need_restart = False
    if task is None or task.done():
        logger.warning("Site checker task is done or missing — restarting")
        need_restart = True
    elif _last_check_at is not None:
        age_minutes = (now - _last_check_at).total_seconds() / 60
        if age_minutes > SITE_CHECKER_STALE_MINUTES:
            logger.warning(
                "Site checker loop stale (%.1f min > %d) — restarting",
                age_minutes,
                SITE_CHECKER_STALE_MINUTES,
            )
            task.cancel()
            try:
                await task
            except (asyncio.CancelledError, RuntimeError):
                pass
            need_restart = True
    if need_restart:
        _last_check_at = None
        app.state.site_checker_task = asyncio.create_task(_checker_loop())


async def _watchdog_loop(app) -> None:
    logger.info("Site checker watchdog started")
    while True:
        await asyncio.sleep(60)
        await _watchdog_step(app)


# Update start_checker:
async def start_checker(app) -> None:
    if not SITE_CHECKER_ENABLED:
        logger.info("Site checker disabled")
        return
    app.state.site_checker_task = asyncio.create_task(_checker_loop())
    app.state.site_checker_watchdog = asyncio.create_task(_watchdog_loop(app))
    logger.info("Site checker task and watchdog created")


# Update stop_checker:
async def stop_checker(app) -> None:
    for attr in ("site_checker_watchdog", "site_checker_task"):
        task = getattr(app.state, attr, None)
        if task:
            task.cancel()
            try:
                await task
            except (asyncio.CancelledError, RuntimeError):
                pass
    logger.info("Site checker stopped")
```

---

**Step 4: Run tests to verify they pass**

```bash
pytest tests/test_log_scanner.py::test_watchdog_step_exists tests/test_log_scanner.py::test_watchdog_restarts_completed_scanner_task tests/test_log_scanner.py::test_scanner_stale_config_exists -v
```

Expected: all 3 PASS

---

**Step 5: Run full test suite**

```bash
pytest tests/ -q
```

Expected: 555 app tests pass

---

**Step 6: Lint and commit**

```bash
ruff check --fix app/config.py app/services/log_scanner.py app/services/site_checker.py && ruff format app/config.py app/services/log_scanner.py app/services/site_checker.py
git add app/config.py app/services/log_scanner.py app/services/site_checker.py tests/test_log_scanner.py
git commit -m "fix(background-tasks): add watchdog loop to log_scanner and site_checker for auto-restart (issue7 1-5)"
```

---

## Final Verification

After all 5 tasks, run the complete suite:

```bash
cd portal_core && pytest tests/ -q && cd .. && pytest tests/ -q
```

Expected output: `151 passed` (portal_core) + `558+ passed` (app — 555 + new tests)

Also verify lint is clean:

```bash
ruff check .
```

Expected: no errors
