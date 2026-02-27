# issue7.md HIGH 問題修正 設計書

> 作成日: 2026-02-27
> 対象: [docs/issue7.md](../issue7.md) の HIGH 優先度 5 件
> アプローチ: 段階的個別修正（TDD — テスト先行、1件ずつ実装）
> 関連: [spec_common_separation.md](../spec_common_separation.md)

---

## 1. 概要

issue7.md で記録された性能・同時アクセス・堅牢性の問題のうち、重大度 HIGH の 5 件を修正する。

各問題を独立したタスクとして TDD（Red → Green → Refactor）で実装し、ロールバック可能な粒度でコミットする。MEDIUM/LOW 問題は別設計書で扱う。

### 修正サマリー

| # | 問題 | 対象ファイル | 修正内容 | テストファイル |
|---|------|------------|---------|--------------|
| 1-1 | WebSocket broadcast 競合 | `portal_core/portal_core/services/websocket_manager.py` | `asyncio.Lock` 追加 | `portal_core/tests/test_websocket.py` |
| 1-2 | Timer TOCTOU | `app/services/task_service.py` | `with_for_update()` でタイマー操作を保護 | `tests/test_tasks.py` |
| 1-3 | Presence N+1 | `app/services/presence_service.py`, `app/crud/presence.py` | JOIN クエリ統合 + タスク上限設定 | `tests/test_presence.py` |
| 1-4 | FTP/SMB サーキットブレーカー | `app/services/log_source_service.py` | 閾値超過で自動無効化 + 指数バックオフ（tenacity） | `tests/test_log_sources.py` |
| 1-5 | バックグラウンドタスク無音失敗 | `app/services/log_scanner.py`, `app/services/site_checker.py`, `main.py` | 最終実行時刻管理 + watchdog + アラート連携 | `tests/test_log_scanner.py`, `tests/test_site_links.py` |

### 実装順序

```
1-1 (WebSocket Lock)   ← 独立
1-2 (Timer TOCTOU)    ← 独立（DB ロック）
1-3 (Presence N+1)    ← 独立（クエリ変更のみ）
1-4 (Circuit Breaker)  ← 独立（consecutive_errors 既存カラム活用）
1-5 (BG Watchdog)     ← 1-4 完了後推奨（アラート連携パターンを再利用）
```

---

## 2. 1-1: WebSocket broadcast 競合状態

### 問題

`WebSocketManager.active_connections` がロックなしの `list` で管理されている。`broadcast()` 実行中に別非同期タスクが `disconnect()` を呼ぶと `ValueError: list.remove(x): x not in list` が発生する。

**影響**: WebSocket 接続の切断・クラッシュ
**対象マネージャー**: 5 件（logs, presence, alerts, calendar, sites）

### 変更ファイル

- `portal_core/portal_core/services/websocket_manager.py`

### 設計

```python
class WebSocketManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []
        self._lock = asyncio.Lock()  # 追加

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        async with self._lock:
            self.active_connections.append(websocket)

    async def disconnect(self, websocket: WebSocket):
        async with self._lock:
            if websocket in self.active_connections:  # ガード追加
                self.active_connections.remove(websocket)

    async def broadcast(self, data: dict):
        # ロック範囲を「コピー取得」と「削除」の 2 箇所に分割
        # send_json() 中はロックを解放してスループットを維持
        async with self._lock:
            connections = self.active_connections.copy()
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
```

### テスト追加

**ファイル**: `portal_core/tests/test_websocket.py`

```python
async def test_broadcast_concurrent_disconnect():
    """broadcast 中に disconnect が呼ばれても ValueError が発生しないこと"""

async def test_disconnect_idempotent():
    """未接続の WebSocket を disconnect しても例外が発生しないこと"""
```

### 検証コマンド

```bash
cd portal_core && pytest tests/test_websocket.py -q && cd ..
```

---

## 3. 1-2: タイマー開始/停止の競合状態（TOCTOU）

### 問題

`start_timer()` がチェック（`get_active_entry`）→ 作成（`start_timer`）の 2 ステップで実行されるため、並行リクエストで同一タスクに複数のアクティブエントリが生成される。`stop_timer()` の `task.total_seconds +=` もロックなしのため、ロストアップデートが発生する。

**影響**: 同一タスクに複数のアクティブエントリ、累計作業時間の計算誤り

### 変更ファイル

- `app/services/task_service.py`

### 設計

```python
from sqlalchemy.orm import Session

def start_timer(db: Session, task_id: int, user_id: int) -> TaskTimeEntry:
    # SELECT ... FOR UPDATE でタスク行をロック
    task = (
        db.query(Task)
        .filter(Task.id == task_id, Task.user_id == user_id)
        .with_for_update()
        .first()
    )
    if not task:
        raise NotFoundError("Task not found")

    active = crud_task.get_active_entry(db, task_id)
    if active:
        raise ConflictError("Timer already running")

    return crud_task.start_timer(db, task)


def stop_timer(db: Session, task_id: int, user_id: int) -> TaskTimeEntry:
    # SELECT ... FOR UPDATE でタスク行をロック（total_seconds += 対策）
    task = (
        db.query(Task)
        .filter(Task.id == task_id, Task.user_id == user_id)
        .with_for_update()
        .first()
    )
    if not task:
        raise NotFoundError("Task not found")

    active = crud_task.get_active_entry(db, task_id)
    if not active:
        raise ConflictError("No active timer")

    elapsed = int((datetime.now(timezone.utc) - active.started_at).total_seconds())
    active.stopped_at = datetime.now(timezone.utc)
    active.elapsed_seconds = elapsed
    task.total_seconds += elapsed  # FOR UPDATE 保護下で安全
    db.flush()
    return active
```

**ポイント**:
- `with_for_update()` はトランザクション完了まで他のトランザクションが同じ行を変更できなくなる（PostgreSQL 行レベルロック）
- `start_timer` と `stop_timer` の両方でロックを取得することで TOCTOU と `total_seconds` ロストアップデートを同時に解消
- マイグレーション不要

### テスト追加

**ファイル**: `tests/test_tasks.py`

```python
def test_start_timer_conflict_returns_400():
    """既にタイマー稼働中のタスクに start を呼ぶと 400 ConflictError になること"""
    # 既存テストで確認済みだが、同一タスクへの二重呼び出しを明示的にテスト

def test_stop_timer_total_seconds_accumulates():
    """stop_timer 後に total_seconds が正しく累積されること（ロストアップデートなし）"""
```

### 検証コマンド

```bash
pytest tests/test_tasks.py -q
```

---

## 4. 1-3: 在籍状態一覧エンドポイントの N+1 相当クエリ

### 問題

`GET /api/presence/statuses` で 3 つのクエリを個別に発行している。進行中タスク取得に上限がなく、WebSocket ブロードキャスト時に毎回呼ばれるため応答時間が悪化する。

**影響**: ユーザー数・タスク数の増加に比例して応答時間が悪化

### 変更ファイル

- `app/crud/presence.py`（新メソッド追加）
- `app/services/presence_service.py`（クエリ削減）

### 設計

```python
# app/crud/presence.py — 新メソッド追加

def get_all_statuses_with_users(
    db: Session,
) -> list[tuple[User, Optional[PresenceStatus]]]:
    """
    users LEFT JOIN presence_statuses で全アクティブユーザーを 1 クエリで取得。
    """
    return (
        db.query(User, PresenceStatus)
        .outerjoin(PresenceStatus, User.id == PresenceStatus.user_id)
        .filter(User.is_active == True)
        .order_by(User.display_name)
        .all()
    )


# app/crud/task.py — 既存メソッドに limit 追加
def get_in_progress_with_backlog(
    db: Session,
    limit: int = 10,  # 上限追加
) -> list[Task]:
    return (
        db.query(Task)
        .filter(Task.status == "in_progress", Task.backlog_ticket_id.isnot(None))
        .limit(limit)
        .all()
    )
```

```python
# app/services/presence_service.py — 修正後

def get_all_statuses(db: Session) -> list[PresenceStatusWithUser]:
    # クエリ1: users + presence_statuses を JOIN で取得（クエリ2を廃止）
    rows = crud_presence.get_all_statuses_with_users(db)

    # クエリ2: 進行中タスク（上限付き）
    active_tasks = crud_task.get_in_progress_with_backlog(db, limit=10)

    # メモリ上でマージ（クエリ3を廃止）
    task_map: dict[int, list[ActiveTicket]] = defaultdict(list)
    for task in active_tasks:
        task_map[task.user_id].append(
            ActiveTicket(
                task_id=task.id,
                task_title=task.title,
                backlog_ticket_id=task.backlog_ticket_id,
            )
        )

    result = []
    for user, status in rows:
        result.append(
            PresenceStatusWithUser(
                user_id=user.id,
                display_name=user.display_name,
                status=status.status if status else "offline",
                message=status.message if status else None,
                updated_at=status.updated_at if status else None,
                active_tickets=task_map.get(user.id, []),
            )
        )
    return result
```

**ポイント**:
- 3 クエリ → 2 クエリに削減（JOIN + 上限付きタスク）
- `limit=10` は `app/config.py` の `PRESENCE_ACTIVE_TASK_LIMIT` 環境変数で設定可能にする
- 非アクティブユーザー（`is_active=False`）が混入する問題（issue7.md 3-3）も同時に解消

### テスト追加

**ファイル**: `tests/test_presence.py`

```python
def test_get_all_statuses_includes_offline_users():
    """presence_status 未設定のユーザーが offline として一覧に含まれること"""

def test_get_all_statuses_excludes_inactive_users():
    """is_active=False のユーザーが一覧に含まれないこと（3-3 の修正も兼ねる）"""

def test_get_all_statuses_active_task_limit():
    """進行中タスクが limit 件を超えないこと"""
```

### 検証コマンド

```bash
pytest tests/test_presence.py -q
```

---

## 5. 1-4: 外部接続（FTP/SMB）のサーキットブレーカー未実装

### 問題

- 接続失敗後もリトライ間隔なしで再試行し続ける
- 複数ソースが同時にハングすると `asyncio.to_thread()` スレッドプールが枯渇する
- `consecutive_errors` カラムは既存だが閾値ロジックがない

**影響**: 外部サーバー障害時に API 全体の応答性が低下

### 変更ファイル

- `app/services/log_source_service.py`
- `app/config.py`（設定追加）
- `requirements.txt`（tenacity 追加）

### 設計

**依存パッケージ追加**: `tenacity>=8.2.0`

```python
# app/config.py に追加
CIRCUIT_BREAKER_THRESHOLD: int = 5   # 連続エラー閾値
CIRCUIT_BREAKER_BACKOFF_MAX: int = 60  # 最大バックオフ秒数
```

```python
# app/services/log_source_service.py

from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    RetryError,
)

def _increment_error(db: Session, source: LogSource, error: str) -> None:
    """エラーをカウントし、閾値超過で自動無効化"""
    source.consecutive_errors += 1
    source.last_error = error
    source.last_checked_at = datetime.now(timezone.utc)

    if source.consecutive_errors >= config.CIRCUIT_BREAKER_THRESHOLD:
        source.is_enabled = False
        logger.warning(
            "LogSource %d disabled after %d consecutive errors: %s",
            source.id,
            source.consecutive_errors,
            error,
        )
        # 既存アラートサービスを活用
        from app.services.alert_service import create_alert_internal
        create_alert_internal(
            db,
            title=f"ログソース '{source.name}' が自動無効化されました",
            message=f"連続 {source.consecutive_errors} 回の接続エラー後に無効化。最終エラー: {error}",
            severity="warning",
            source="circuit_breaker",
        )
    db.commit()


def _reset_error(db: Session, source: LogSource) -> None:
    """成功時にエラーカウントをリセット"""
    source.consecutive_errors = 0
    source.last_error = None
    source.last_checked_at = datetime.now(timezone.utc)
    db.commit()


def _make_retry_decorator():
    return retry(
        retry=retry_if_exception_type(Exception),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=config.CIRCUIT_BREAKER_BACKOFF_MAX),
        reraise=True,
    )


def scan_source(db: Session, source: LogSource) -> ScanResult:
    """スキャン実行（サーキットブレーカー付き）"""
    if not source.is_enabled:
        return ScanResult(skipped=True)

    @_make_retry_decorator()
    def _do_scan():
        return _scan_remote(source)

    try:
        result = _do_scan()
        _reset_error(db, source)
        return result
    except (RetryError, Exception) as e:
        _increment_error(db, source, str(e))
        raise
```

**スキャン実行フロー**:

```
scan_source() 呼び出し
  → is_enabled チェック（False なら即スキップ）
  → _do_scan()（3 回リトライ、指数バックオフ 1s/2s/4s...最大 60s）
    → 成功: _reset_error()（consecutive_errors = 0）
    → 失敗: _increment_error()
        → consecutive_errors >= CIRCUIT_BREAKER_THRESHOLD で is_enabled=False + アラート生成
```

### テスト追加

**ファイル**: `tests/test_log_sources.py`

```python
def test_circuit_breaker_disables_after_threshold(client, db_session):
    """CIRCUIT_BREAKER_THRESHOLD 回連続エラーで is_enabled が False になること"""

def test_circuit_breaker_resets_on_success(client, db_session):
    """成功時に consecutive_errors が 0 にリセットされること"""

def test_circuit_breaker_creates_alert_on_disable(client, db_session):
    """自動無効化時にアラートが生成されること"""

def test_circuit_breaker_skips_disabled_source(client, db_session):
    """is_enabled=False のソースがスキャンをスキップすること"""
```

### 検証コマンド

```bash
pytest tests/test_log_sources.py -q
```

---

## 6. 1-5: バックグラウンドタスクの無音失敗

### 問題

`log_scanner.py`・`site_checker.py` の例外処理がログ出力のみで、タスクが停止しても検知・復旧する仕組みがない。ヘルスチェック手段もない。

**影響**: 監視データが古くなっても誰も気づかない。アラートシステム自体の障害がアラートされない。

### 変更ファイル

- `app/services/log_scanner.py`
- `app/services/site_checker.py`
- `main.py`
- `app/config.py`（設定追加）

### 設計

**共通パターン**（log_scanner / site_checker 両方に適用）:

```python
# app/services/log_scanner.py

import asyncio
from datetime import datetime, timezone, timedelta
from typing import Optional

_last_scan_at: Optional[datetime] = None
_STALE_THRESHOLD_MINUTES = 15  # 設定可能（config.LOG_SCANNER_STALE_MINUTES）


async def _scan_due_sources(db_factory) -> None:
    global _last_scan_at
    try:
        # ... 既存のスキャンロジック
        pass
    except Exception:
        logger.exception("Error in scan_due_sources")
    finally:
        # 例外が発生してもタイムスタンプを更新（ループ継続の証拠）
        _last_scan_at = datetime.now(timezone.utc)


async def watchdog(db_factory, stale_minutes: int = 15) -> None:
    """バックグラウンドタスクの生存監視ループ"""
    threshold = timedelta(minutes=stale_minutes)
    while True:
        await asyncio.sleep(300)  # 5 分ごとにチェック
        if _last_scan_at is None:
            continue
        elapsed = datetime.now(timezone.utc) - _last_scan_at
        if elapsed > threshold:
            logger.error(
                "Log scanner stalled. Last run: %s ago",
                elapsed,
            )
            db = next(db_factory())
            try:
                from app.services.alert_service import create_alert_internal
                create_alert_internal(
                    db,
                    title="ログスキャナーが停止しています",
                    message=f"最終実行から {elapsed} 経過しています。サーバーを確認してください。",
                    severity="critical",
                    source="scanner_watchdog",
                )
            finally:
                db.close()


def get_last_scan_at() -> Optional[datetime]:
    """ヘルスチェック・テスト用"""
    return _last_scan_at
```

```python
# main.py — タスク管理強化

async def _run_with_restart(coro_factory, name: str, restart_delay: int = 10):
    """クラッシュ時に自動再起動するラッパー"""
    while True:
        try:
            await coro_factory()
        except Exception:
            logger.exception("%s crashed, restarting in %ds", name, restart_delay)
            await asyncio.sleep(restart_delay)

# startup イベント内
if config.LOG_SCANNER_ENABLED:
    asyncio.create_task(
        _run_with_restart(log_scanner.start, "log_scanner"),
        name="log_scanner",
    )
    asyncio.create_task(
        log_scanner.watchdog(get_db, stale_minutes=config.LOG_SCANNER_STALE_MINUTES),
        name="log_scanner_watchdog",
    )

if config.SITE_CHECKER_ENABLED:
    asyncio.create_task(
        _run_with_restart(site_checker.start, "site_checker"),
        name="site_checker",
    )
    asyncio.create_task(
        site_checker.watchdog(get_db, stale_minutes=config.SITE_CHECKER_STALE_MINUTES),
        name="site_checker_watchdog",
    )
```

```python
# app/config.py に追加
LOG_SCANNER_STALE_MINUTES: int = 15   # スキャナー停止アラート閾値（分）
SITE_CHECKER_STALE_MINUTES: int = 15  # チェッカー停止アラート閾値（分）
```

### テスト追加

**ファイル**: `tests/test_log_scanner.py`

```python
async def test_watchdog_creates_alert_when_stalled(db_session):
    """スキャナーが stale_minutes 以上実行されない場合にアラートが生成されること"""

def test_last_scan_at_updates_after_scan():
    """スキャン実行後に get_last_scan_at() が更新されること"""

async def test_run_with_restart_restarts_after_crash():
    """スキャナーがクラッシュしても _run_with_restart が再起動すること"""
```

**ファイル**: `tests/test_site_links.py`

```python
async def test_site_checker_watchdog_creates_alert_when_stalled(db_session):
    """チェッカーが stale_minutes 以上実行されない場合にアラートが生成されること"""
```

### 検証コマンド

```bash
pytest tests/test_log_scanner.py tests/test_site_links.py -q
```

---

## 7. 依存パッケージ変更

| パッケージ | バージョン | 用途 | 追加先 |
|-----------|----------|------|--------|
| `tenacity` | `>=8.2.0` | 指数バックオフ付きリトライ（1-4） | `requirements.txt` |

---

## 8. 設定項目追加（app/config.py）

| 設定名 | デフォルト値 | 説明 |
|--------|------------|------|
| `CIRCUIT_BREAKER_THRESHOLD` | `5` | 連続エラー閾値（超過で自動無効化） |
| `CIRCUIT_BREAKER_BACKOFF_MAX` | `60` | 最大バックオフ秒数 |
| `PRESENCE_ACTIVE_TASK_LIMIT` | `10` | 在籍状態に表示する進行中タスクの上限数 |
| `LOG_SCANNER_STALE_MINUTES` | `15` | スキャナー停止アラートの閾値（分） |
| `SITE_CHECKER_STALE_MINUTES` | `15` | チェッカー停止アラートの閾値（分） |

---

## 9. 全テスト実行コマンド

```bash
# portal_core テスト（1-1 の WebSocket 修正を含む）
cd portal_core && pytest tests/test_websocket.py -q && cd ..

# アプリテスト（1-2〜1-5）
pytest tests/test_tasks.py tests/test_presence.py tests/test_log_sources.py tests/test_log_scanner.py tests/test_site_links.py -q

# 全テスト（最終確認）
cd portal_core && pytest tests/ -q && cd .. && pytest tests/ -q

# Lint
ruff check --fix . && ruff format .
```

---

## 10. 副次的修正

1-3（Presence N+1）の修正により、issue7.md **3-3**（在籍状態への非アクティブユーザー混入）も同時に解消される（`filter(User.is_active == True)` を JOIN クエリに追加）。

---

## 11. 参考

- [issue7.md](../issue7.md) — 問題の詳細記述
- [spec_common_separation.md](../spec_common_separation.md) — portal_core 設計書
- [spec_nonfunction.md](../spec_nonfunction.md) — 非機能要件・テスト仕様
