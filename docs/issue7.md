# ISSUE-7: 性能・同時アクセス・堅牢性に関する問題点

作成日: 2026-02-26
対象: Todo List Portal 全体
ステータス: **HIGH 優先度 対応済み（2026-02-27）、MEDIUM 優先度 対応済み（2026-02-27）、LOW 未対応**

---

## 概要

現行実装において、性能（パフォーマンス）、同時アクセス（並行性）、堅牢性（ロバストネス）の観点で以下の問題が確認された。本ドキュメントは技術的負債の記録として残し、優先度に従って対応を進める。

---

## 1. 重大度: HIGH（高）

### 1-1. WebSocket ブロードキャストの競合状態 ✅ 対応済み

**ファイル:** `portal_core/portal_core/services/websocket_manager.py`

**問題:**
`active_connections` がロックなしの `list` で管理されている。複数の非同期タスクが同時に `broadcast()` を呼び出すと、リストの変更中に別タスクが同時変更を行い、`ValueError: list.remove(x): x not in list` 例外が発生する可能性がある。

```python
async def broadcast(self, data: dict):
    for connection in self.active_connections[:]:   # ← コピー時点と削除時点でリストが変わる
        try:
            await connection.send_json(data)
        except Exception:
            disconnected.append(connection)
    for conn in disconnected:
        self.active_connections.remove(conn)  # ← 競合: 別タスクが既に削除済みの場合
```

**影響:** WebSocket 接続の切断、クラッシュ
**対象マネージャー:** 5件（logs, presence, alerts, calendar, sites）

**対応内容（2026-02-27）:**
`asyncio.Lock` を `WebSocketManager` に追加し、`connect` / `disconnect` / `broadcast` をロック保護。ブロードキャスト時はロックを保持しない（送信はロックの外）で一貫性と並行性を両立。
- テスト追加: `portal_core/tests/test_websocket.py` に `TestWebSocketAsync` クラス（非同期並行テスト2件）追加

---

### 1-2. タイマー開始/停止の競合状態（TOCTOU） ✅ 対応済み

**ファイル:** `app/services/task_service.py`

**問題:**
タイマー開始・停止がチェック→操作の2ステップで実行され、その間に別リクエストが割り込む可能性がある（Time-of-Check to Time-of-Use 問題）。

```python
def start_timer(db, task_id, user_id):
    active = crud_task.get_active_entry(db, task_id)  # T1: チェック
    if active:
        raise ConflictError("Timer already running")
    entry = crud_task.start_timer(db, task)           # T2: 作成（T1とT2の間に別リクエストが侵入可能）
```

また、`stop_timer` 内の `task.total_seconds += elapsed` はロックなしの `+=` のため、同時呼び出しで計測時間が失われる（ロストアップデート）。

**影響:** 同一タスクに複数のアクティブエントリが生成される。累計作業時間の計算誤り。

**対応内容（2026-02-27）:**
`app/crud/task.py` の `get_task_for_update()` に `SELECT ... FOR UPDATE` を追加し、`start_timer` / `stop_timer` サービス関数で行レベルロックを取得してからチェック・更新を実行。ロストアップデートも解消。
- テスト追加: `tests/test_tasks.py` に TOCTOU/ロストアップデート検証テスト3件追加

---

### 1-3. 在籍状態一覧エンドポイントの N+1 相当クエリ ✅ 対応済み

**ファイル:** `app/services/presence_service.py`

**問題:**
`GET /api/presence/statuses` で3つのクエリを個別に発行している。

```python
def get_all_statuses(db):
    statuses = crud_presence.get_all_presence_statuses(db)  # クエリ1
    users = crud_user.get_users(db, active_only=True)       # クエリ2（全ユーザー取得）
    active_tasks = crud_task.get_in_progress_with_backlog(db)  # クエリ3（全進行中タスク）
```

- アクティブユーザー数が増えると3クエリの合計レコード数が膨大になる
- 進行中タスク取得に上限がない
- ステータス更新のたびに WebSocket ブロードキャストで呼び出される可能性がある

**影響:** ユーザー数・タスク数の増加に比例して応答時間が悪化（数百ms〜数秒）。

**対応内容（2026-02-27）:**
`app/crud/task.py` の `get_in_progress_with_backlog()` に `limit` パラメータを追加。`app/config.py` に `PRESENCE_ACTIVE_TASK_LIMIT`（デフォルト 50）を追加し、`presence_service.py` で上限を適用。クエリは3本のまま維持（JOIN化は将来課題）だが、タスク取得の無制限増大を防止。
- テスト追加: `tests/test_presence.py` に上限制御の検証テスト2件追加

---

### 1-4. 外部接続（FTP/SMB）のサーキットブレーカー未実装 ✅ 対応済み（部分）

**ファイル:** `app/services/log_source_service.py`, `app/services/log_scanner.py`

**問題:**
- FTP/SMB 接続にタイムアウト保護はあるが、スレッドプール外（非メインスレッド）では `SIGALRM` が動作しないため、実質的にタイムアウトが機能しない場合がある
- 接続失敗後もリトライ間隔なしで再試行し続ける
- 複数ソースが同時にハングすると `asyncio.to_thread()` スレッドプールが枯渇する
- サーキットブレーカー（連続失敗検知→一時停止→回復テスト）が未実装

```python
# log_source_service.py
@contextmanager
def _path_timeout(seconds: int):
    if seconds <= 0 or not hasattr(signal, "SIGALRM"):
        yield  # ← タイムアウトなしでそのまま処理
        return
```

**影響:** 外部サーバー障害時にバックグラウンドスキャナーが応答不能になり、API 全体の応答性が低下する。

**対応内容（2026-02-27）:**
`app/crud/log_source.py` の `update_scan_state()` にサーキットブレーカーロジックを追加。`app/config.py` に `LOG_SOURCE_MAX_CONSECUTIVE_FAILURES`（デフォルト 5）を追加し、連続失敗が閾値に達したソースを自動的に `is_enabled=False` に変更。警告ログを出力。
- 未解決: SIGALRM タイムアウト問題・指数バックオフは対象外（将来課題）
- テスト追加: `tests/test_log_sources.py` に 4件追加（設定値確認・自動無効化・成功時リセット・HTTP エンドポイント経由の統合テスト）

---

### 1-5. バックグラウンドタスクの無音失敗 ✅ 対応済み

**ファイル:** `app/services/log_scanner.py`, `app/services/site_checker.py`

**問題:**
スキャナー・チェッカーの例外処理がログ出力のみで、タスクが停止しても検知・復旧する仕組みがない。

```python
async def _scan_due_sources():
    try:
        # ...
    except Exception:
        logger.exception("Error in scan_due_sources")  # ← ログ記録のみ、復旧なし
```

**影響:**
- 監視データが古くなっても誰も気づかない
- 皮肉なことに、アラートシステム自体の障害がアラートされない
- バックグラウンドタスクのヘルスチェック手段がない

**対応内容（2026-02-27）:**
`log_scanner.py` / `site_checker.py` の両方にウォッチドッグパターンを実装:
- `_last_scan_at` / `_last_check_at` モジュール変数でループ最終実行時刻を追跡
- `_watchdog_step()`: タスクが `done()` の場合または最終実行が `LOG_SCANNER_STALE_MINUTES` / `SITE_CHECKER_STALE_MINUTES`（デフォルト 10 分）を超えた場合に自動再起動
- `_watchdog_loop()`: 60 秒ごとにウォッチドッグを実行
- `start_scanner()` / `start_checker()`: メインタスクとウォッチドッグの両方を起動
- `stop_scanner()` / `stop_checker()`: ウォッチドッグを先にキャンセルしてからメインタスクをキャンセル（再起動防止）
- テスト追加: `tests/test_log_scanner.py` に 3件追加（ウォッチドッグ存在確認・完了タスクの再起動・設定値確認）

---

## 2. 重大度: MEDIUM（中）

### 2-1. タスクリスト開始操作の競合状態 ✅ 対応済み

**ファイル:** `app/services/task_list_service.py`

**問題:**
`start_as_task()` でアイテムの重複開始チェックと実際の作成の間に競合ウィンドウが存在する。

```python
def start_as_task(db, item_id, user_id):
    existing_count = crud_task.count_by_source_item_id(db, item.id)  # T1: チェック
    if existing_count > 0:
        raise ConflictError("A task already exists for this item")
    task = svc_task.create_and_start_task(...)  # T2: 作成（競合ウィンドウ）
    item.assignee_id = user_id  # T3: 二重割り当て発生の可能性
```

**影響:** 1つのアイテムに複数のタスクが生成される可能性。

**対応内容（2026-02-27）:**
`app/crud/task_list_item.py` に `get_item_for_update()` 関数を追加し、`SELECT ... FOR UPDATE` で行レベルロックを取得。`app/services/task_list_service.py` の `start_as_task()` でロック付き取得に切り替えることで、チェック→作成の競合ウィンドウを解消。

---

### 2-2. 一覧エンドポイントのページネーション未実装 ✅ 対応済み

**ファイル:** 複数ルーター

以下のエンドポイントにページネーション（`limit`/`offset`）が実装されていない。

| エンドポイント | ファイル | 問題 |
|--------------|---------|------|
| `GET /api/tasks/` | `app/routers/api_tasks.py` | 全件取得 |
| `GET /api/task-list/all` | `app/routers/api_task_list.py` | 全件取得 |
| `GET /api/alert-rules/` | `app/routers/api_alert_rules.py` | 全件取得 |
| `GET /api/wiki/pages/` | `app/routers/api_wiki.py` | 全件取得 |
| `GET /api/presence/statuses` | `app/routers/api_presence.py` | 全件取得 |

**影響:** データ量増加に伴いメモリ枯渇・応答時間悪化。大規模運用でOOMリスク。

**対応内容（2026-02-27）:**
`GET /api/tasks/`、`GET /api/task-list/all`、`GET /api/alert-rules/`、`GET /api/wiki/pages/`、`GET /api/presence/statuses` の5エンドポイントに `limit`（デフォルト 200）・`offset`（デフォルト 0）クエリパラメータを追加。CRUD 層の対応関数にも同パラメータを追加し、後方互換を維持しつつ大規模データでのページ分割取得が可能になった。`GET /api/task-list/unassigned`、`GET /api/task-list/mine`、`GET /api/reports/all` は今回の対象外（将来課題）。

---

### 2-3. DB 接続プール設定の最適化不足 ✅ 対応済み（部分）

**ファイル:** `portal_core/portal_core/database.py`

**問題:**
デフォルトの SQLAlchemy 接続プール設定では、同時アクセス数が多い場合にプールが枯渇する。また、`get_db()` ジェネレータでの明示的なロールバックが不足している。

```python
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()  # ← 例外発生時の明示的ロールバックなし
```

**影響:** 高負荷時の接続待ちタイムアウト、トランザクション残留の可能性。

**対応内容（2026-02-27）:**
`portal_core/portal_core/database.py` の `get_db()` に `except Exception: db.rollback(); raise` を追加し、例外発生時の明示的ロールバックを実装。トランザクション残留リスクを解消。
- `pool_size`・`max_overflow` チューニングは環境依存のため未実施（将来課題）
- テスト追加: `portal_core/tests/test_crud_base.py` に `TestGetDbRollback` クラスを追加しロールバック動作を検証

---

### 2-4. 同時ログイン時のセッション競合 ✅ 対応済み

**ファイル:** `portal_core/portal_core/routers/api_auth.py`

**問題:**
ログイン処理が `session.clear()` → フィールド設定の2ステップで行われるため、同一ユーザーの別リクエストが `clear()` 後のウィンドウで認証エラーになる可能性がある。

```python
request.session.clear()          # T1: セッション消去
request.session["user_id"] = ... # T2: 再設定（T1とT2の間に別リクエストが 401 を受ける）
```

**影響:** まれに「セッションが切れた」という誤ったエラーが発生する。

**対応内容（2026-02-27）:**
`portal_core/portal_core/routers/api_auth.py` のログイン処理で、個別フィールド設定を `session.update({...})` による一括設定に変更。`session.clear()` 後のアトミック書き込みで競合ウィンドウを解消。
- テスト追加: `portal_core/tests/test_auth.py` に `TestLoginSessionAtomic` クラスを追加しセッション一括更新の動作を検証

---

### 2-5. バッチ完了操作の楽観的ロック不在 ✅ 対応済み

**ファイル:** `app/services/task_service.py`

**問題:**
`batch_done()` でタスクを一括取得してから削除するまでの間に、別リクエストで対象タスクが削除された場合でも静かに処理が続く可能性がある。

**影響:** 既に削除されたタスクがバッチ結果に含まれる、または `db.delete()` でエラーが発生する。

**対応内容（2026-02-27）:**
`app/crud/task.py` に `get_tasks_by_ids_for_update()` 関数を追加し、`SELECT ... FOR UPDATE` で複数タスクを行レベルロック付き一括取得。`app/services/task_service.py` の `batch_done()` でロック付き取得に切り替え、取得後に各タスクの存在確認（`user_id` チェック含む）を実施。ロック後に消えたタスクはスキップするフォールバック処理も追加。
- テスト追加: `tests/test_tasks.py` に `TestBatchDoneForUpdate` クラスを追加し SELECT FOR UPDATE 動作を検証

---

## 3. 重大度: LOW（低）

### 3-1. WebSocket ハートビート未実装

**ファイル:** `portal_core/portal_core/app_factory.py`

WebSocket のキープアライブ（ping/pong）が実装されていない。ネットワーク障害による切断がサーバー側で即座に検知されず、ゾンビ接続が `active_connections` に残存する。

**対応:** `receive_text()` にタイムアウトを設定するか、定期的な ping を実装する。

---

### 3-2. Excel エクスポートのメモリ使用

**ファイル:** `app/services/attendance_service.py`

Excel ファイル生成時にファイル全体を `BytesIO` でメモリに保持する。同時に複数ユーザーが大量データのエクスポートを実行すると、メモリ消費が急増する。

**対応:** ストリーミングレスポンス（`StreamingResponse`）の検討。

---

### 3-3. `presence_service` の非アクティブユーザー混入

**ファイル:** `app/services/presence_service.py`

在籍状態一覧に非アクティブユーザーのフィルタリングが不完全で、削除済みユーザーのステータスが残存する可能性がある。

---

### 3-4. 暗号化失敗時のクレデンシャル平文保存リスク

**ファイル:** `app/services/log_source_service.py`

暗号化ライブラリが利用不可の場合は `ConflictError` を返すが、`encrypt_value()` の内部エラー（鍵破損等）でサイレントに平文を返す実装になっていないか要確認。クレデンシャルの平文 DB 保存が発生しうる。

---

## 対応優先度まとめ

| 優先度 | 番号 | 問題 | 対応状況 |
|--------|------|------|---------|
| **HIGH** | 1-1 | WebSocket broadcast 競合 | ✅ 対応済み（`asyncio.Lock` 追加） |
| **HIGH** | 1-2 | タイマー TOCTOU | ✅ 対応済み（`SELECT FOR UPDATE` 導入） |
| **HIGH** | 1-3 | 在籍状態 N+1 クエリ | ✅ 対応済み（上限設定 `PRESENCE_ACTIVE_TASK_LIMIT`） |
| **HIGH** | 1-4 | FTP/SMB サーキットブレーカー不在 | ✅ 対応済み（部分: 自動無効化のみ、バックオフは将来課題） |
| **HIGH** | 1-5 | バックグラウンドタスク無音失敗 | ✅ 対応済み（ウォッチドッグパターン追加） |
| **MEDIUM** | 2-1 | タスクリスト start 競合 | ✅ 対応済み（`SELECT FOR UPDATE` + `get_item_for_update()` 追加） |
| **MEDIUM** | 2-2 | ページネーション不在 | ✅ 対応済み（tasks・task-list/all・alert-rules・wiki・presence 5エンドポイントに limit/offset 追加） |
| **MEDIUM** | 2-3 | DB 接続プール設定 | ✅ 対応済み（部分: `get_db()` 明示的ロールバック追加。pool_size は将来課題） |
| **MEDIUM** | 2-4 | ログイン時セッション競合 | ✅ 対応済み（`session.update()` による一括設定） |
| **MEDIUM** | 2-5 | バッチ完了の楽観ロック不在 | ✅ 対応済み（`SELECT FOR UPDATE` + `get_tasks_by_ids_for_update()` 追加） |
| **LOW** | 3-1 | WS ハートビート不在 | 未対応 — ping/pong 実装推奨 |
| **LOW** | 3-2 | Excel メモリ使用 | 未対応 — StreamingResponse 検討 |
| **LOW** | 3-3 | 在籍状態 非アクティブユーザー混入 | 未対応 — フィルタ修正推奨 |
| **LOW** | 3-4 | 暗号化失敗リスク | 未対応 — encrypt_value の例外処理確認推奨 |

---

## 参考

- [spec_nonfunction.md](./spec_nonfunction.md) — 非機能要件・テスト仕様
- [spec_log_problem.md](./spec_log_problem.md) — ログ関連問題点（別ドキュメント）
- [spec_common_separation.md](./spec_common_separation.md) — portal_core 分離設計書（技術的負債セクション参照）
