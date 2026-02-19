# ISSUE5: システム課題（セキュリティ・性能・拡張性・再利用性）

> 最新時点で残存する問題点・矛盾点を、セキュリティ・性能・拡張性・モジュール再利用性の4観点で整理。
> ISSUE3/4 で既知・解決済みの項目は除外。
>
> 重要度: **Critical** > **High** > **Medium** > **Low**

---

## 1. セキュリティ

### ISSUE-053: UserCreate/UserUpdate の role フィールドが未検証 [High] ✅ 解消済み

**現象**: `app/schemas/user.py` の `UserCreate.role` は `str = "user"` 型。任意の文字列値（`"superadmin"` 等）が受け入れられていた。

**対処**: `UserCreate.role` を `Literal["admin", "user"]`、`UserUpdate.role` を `Optional[Literal["admin", "user"]]` に変更。不正な値は Pydantic バリデーションで 422 エラーとなる。

---

### ISSUE-054: attendance_presets エンドポイントに認証 Depends なし [Medium] ✅ 解消済み

**現象**: `app/routers/api_attendance_presets.py` の `list_presets()` に `Depends(get_current_user_id)` がなかった。

**対処**: `_user_id: int = Depends(get_current_user_id)` を追加。他の全エンドポイントと一貫した防御の多層化を実現。

---

### ISSUE-055: パスワード強度検証なし [Medium] ✅ 解消済み

**現象**: ユーザー作成・パスワード変更時にパスワードの最小長・複雑さのチェックがない。1文字のパスワードでも受け入れられる。

**該当**: `user_service.py` — `create_user()`, `change_password()`, `admin_reset_password()`

**対処案**: `Field(min_length=8)` またはサービス層でのバリデーション。

**解消**: Security Enhancement Phase で `app/core/auth/password_policy.py` を実装済み。最小8文字、大文字/小文字/数字必須（設定可能）。

---

### ISSUE-065: SECRET_KEY のデフォルト値が予測可能 [Critical] ✅ 解消済み

**現象**: `app/config.py` で SECRET_KEY のデフォルト値がソースコードにハードコードされていた。

**対処**: デフォルト値を空文字 `""` に変更。環境変数（`.env`）での設定が必須となり、予測可能なデフォルト鍵による Cookie 偽造リスクを解消。

---

### ISSUE-066: DEFAULT_PASSWORD が "admin" [High] ✅ 解消済み

**現象**: `app/config.py` のデフォルトパスワードが `"admin"` で推測容易だった。

**対処**: デフォルト値を空文字 `""` に変更。環境変数（`.env`）での設定が必須。推測可能なデフォルトパスワードのリスクを解消。

---

### ISSUE-067: TaskListItem の parent_id に権限チェックなし [High] ✅ 該当なし

**現象**: `task_list_service.py:45-49` の `create_item()` で、`parent_id` 指定時に親アイテムの存在確認のみ行い、ユーザーの閲覧権限を検証しない。

**解消**: `parent_id` カラムはマイグレーション `4f88001d4f7c` で削除済み。TaskListItem に親子階層の概念が存在しないため、本課題は該当なし。

---

### ISSUE-068: get_children() が子アイテムの閲覧権限を未検証 [Medium] ✅ 該当なし

**現象**: `task_list_service.py:68-70` で、親アイテムの閲覧権限は検証するが、返却する子アイテムのフィルタリングを行わない。

**解消**: ISSUE-067 と同様、`parent_id` カラム削除済みにより children 機能自体が存在しない。該当なし。

---

### ISSUE-069: POST /api/logs/ にレート制限・サイズ制限なし [Medium]

**現象**: `api_logs.py:15-18` の公開エンドポイント（認証不要）に対するレート制限がない。

```python
@router.post("/", response_model=LogResponse, status_code=201)
async def create_log(data: LogCreate, db: Session = Depends(get_db)):
    """Public endpoint for external log ingestion."""
    return await svc_log.create_log(db, data)
```

`LogCreate` スキーマの `message: str` にも文字数制限がない。

```python
class LogCreate(BaseModel):
    system_name: str   # 長さ制限なし
    log_type: str      # 長さ制限なし
    message: str       # 長さ制限なし — 数MB のメッセージも送信可能
    extra_data: Optional[Any] = None  # 任意のJSON — ネスト深度制限なし
```

**影響**: 外部から大量のリクエスト送信でDB肥大化、巨大メッセージでメモリ圧迫。さらに各ログで全アラートルール評価（ISSUE-074）が走るため、DoS 増幅効果がある。

**対処案**:
- `message` に `Field(max_length=10000)` 等の制限追加
- `system_name`, `log_type` に `Field(max_length=200)` 制限追加
- レート制限ミドルウェア（SlowAPI 等）の導入検討

---

### ISSUE-070: SessionMiddleware の secure/samesite がデフォルトで弱い [Low]

**現象**: `app/config.py:20-21` でセッション Cookie の設定がデフォルトで `secure=False`, `samesite=lax`。

```python
SESSION_COOKIE_SECURE: bool = os.environ.get("SESSION_COOKIE_SECURE", "false").lower() == "true"
SESSION_COOKIE_SAMESITE: str = os.environ.get("SESSION_COOKIE_SAMESITE", "lax")
```

**影響**: HTTP 通信でセッション Cookie が送信され、中間者攻撃でセッションハイジャックの可能性。開発環境では問題ないが、本番環境設定を忘れるリスク。

**対処案**: 本番環境チェックリストに追加、またはデフォルトを `secure=True` に変更。

---

### ISSUE-071: CSRF ミドルウェアが Origin/Referer なしのリクエストを許可 [Low]

**現象**: `main.py:57-80` の CSRF ミドルウェアで、Origin ヘッダも Referer ヘッダもないリクエストは検証なしで通過する。

```python
if origin:
    # origin チェック
elif referer:
    # referer チェック
# どちらもない場合 → そのまま通過
```

**影響**: 古いブラウザや特殊な設定では Origin/Referer なしで CSRF が成立する可能性がある。ただし SameSite=lax Cookie と組み合わせで実質的リスクは低い。

**備考**: 「非ブラウザクライアント（curl 等）を許可する」設計意図があるためトレードオフ。

---

## 2. 性能（パフォーマンス）

### ISSUE-063: 主要テーブルの FK カラムにインデックスなし [High]

**現象**: PostgreSQL は FK に対して自動でインデックスを作成しない。頻繁にクエリされる FK カラムにインデックスが欠如。

| テーブル | カラム | 主なクエリ |
|---------|--------|-----------|
| `tasks` | `user_id` | `get_tasks(db, user_id)` — 全ユーザーアクセス |
| `tasks` | `category_id` | JOIN on task categories |
| `attendances` | `user_id` | `get_attendances(db, user_id)` — 全勤怠一覧 |
| `daily_reports` | `user_id` | `get_reports_by_user(db, user_id)` — 日報一覧 |
| `daily_reports` | `category_id` | サマリー集計時の JOIN |
| `task_list_items` | `assignee_id` | `get_assigned_items(db, user_id)` — 自分のアイテム |
| `task_list_items` | `created_by` | 作成者フィルタ |
| `task_list_items` | `parent_id` | `get_children(db, item_id)` — 子アイテム |
| `alerts` | `rule_id` | ルール別アラート検索 |

> `users.group_id` は既に `index=True` が設定されている（唯一の例外）。

**影響**: 各テーブルが数千行を超えた時点で、WHERE 句によるフィルタが全件スキャンになりレスポンスが劣化。特に `tasks.user_id`（全タスク画面）と `attendances.user_id`（勤怠一覧）は頻度が高い。

**対処案**: Alembic マイグレーションで一括インデックス追加。

```python
# 例: models/task.py
user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
```

---

### ISSUE-072: attendance_service の N+1 クエリ [High] ✅ 解消済み

**現象**: `attendance_service.py:88` の `list_attendances()` が、各勤怠レコードに対して個別に `_attach_breaks()` を呼び出し、その中で `crud_break.get_breaks(db, att.id)` を実行。

```python
def list_attendances(db, user_id, year=None, month=None):
    attendances = crud_att.get_attendances(db, user_id, year=year, month=month)
    return [_attach_breaks(db, att) for att in attendances]  # N回の追加クエリ
```

**影響**: 月次勤怠一覧（約20-22件）でクエリ数が `1 + 22 = 23` 。年間表示や Excel 出力（`generate_monthly_excel`）でも同パターン。

**対処案**:
- 案A: `joinedload(Attendance.breaks)` で一括読み込み（リレーション追加が必要）
- 案B: `get_breaks_by_attendance_ids(db, att_ids)` でバッチ取得してメモリ結合

**解消**: ISSUE-083 の対処（attendance_service dict→ORM リファクタリング）の副次効果として解消。`Attendance` モデルに `breaks = relationship(..., lazy="selectin")` を追加したことで、`list_attendances` は 1 + 1 (SELECT IN) = 2 クエリに削減。月次約22件で 23クエリ → 2クエリ。

---

### ISSUE-074: アラートルール評価が全ログで O(n) [Medium]

**現象**: `alert_service.py:114-132` で、ログ1件ごとに全有効ルールを DB から取得して全件評価。

```python
async def evaluate_rules_for_log(db, log_data):
    rules = crud_alert.get_enabled_alert_rules(db)  # 毎回全件取得
    for rule in rules:                               # O(n) ルール評価
        if _matches_condition(rule.condition, log_data):
            # アラート作成 + WebSocket broadcast
```

**影響**: ログ収集が有効な場合（`LOG_COLLECTOR_ENABLED=true`）、ポーリング間隔（5秒）で取得された複数行 × ルール数の評価が走る。ルール20件 × ログ100件/分 = 2000回/分の評価。

**対処案**:
- ルールをアプリケーションレベルでキャッシュ（ルール CUD 時にキャッシュ更新）
- `condition` の `field` を事前インデックス化して該当ルールのみ評価

---

### ISSUE-075: summary_service がレポート全件をメモリに読み込み [Medium] ✅ 解消済み（部分）

**現象**: `summary_service.py:53` で期間内の全レポートを一括取得し、Python 上で複数回イテレーション（ユーザー集計、日付集計、カテゴリ集計、課題抽出）。

```python
all_reports = crud_report.get_reports_by_date_range(db, period_start, period_end)
# → 以降、同じリストを8回走査（Counter×2、set×1、explicit loop×5）
```

**影響**: 月次サマリーで100ユーザー × 22日 × 平均3件 = 約6,600レポート。全て ORM オブジェクトとしてメモリ保持。現時点では問題ないが、ユーザー増加時にスケールしない。

**対処（済み）**: メモリ上の8回走査を単一ループに統合。`for r in reports:` 1回で全集計（ユーザー別カウント・日付別カウント・カテゴリ別集計・最近10件・課題抽出）を完了。`Counter`/`defaultdict` を初期化し、ループ内で全アキュムレータを同時更新。

**残存課題**: DB レベルの `GROUP BY` 集計クエリへの変更は未実施。大規模データでは引き続きメモリ使用量が増加する。

---

### ISSUE-076: 主要リストエンドポイントにページネーションなし [Medium]

**現象**: 以下のエンドポイントが全件返却。

| エンドポイント | 現状 |
|--------------|------|
| `GET /api/todos/` | 全件（user_id フィルタのみ） |
| `GET /api/tasks/` | 全件（user_id フィルタのみ） |
| `GET /api/attendances/` | year/month フィルタのみ（最大約31件） |
| `GET /api/reports/` | 全件または日付フィルタ |
| `GET /api/task-list/unassigned` | 全件 |
| `GET /api/task-list/mine` | 全件 |
| `GET /api/todos/public` | 全件 |

**影響**: 長期運用で Todo やタスクが蓄積するとレスポンスサイズが増大。

**対処案**: `limit` + `offset` パラメータ追加、デフォルト `limit=50`。

---

### ISSUE-077: WebSocket broadcast が全接続に一括送信 [Low]

**現象**: `websocket_manager.py` の `broadcast()` は全アクティブ接続に送信。

```python
async def broadcast(self, data: dict):
    for connection in self.active_connections[:]:
        await connection.send_json(data)  # 全接続に送信
```

**影響**:
- **ログ WS**: 全ユーザーに全ログが送信される（適切）
- **プレゼンス WS**: 全ユーザーに全ステータス変更が送信される（適切）
- **アラート WS**: 全ユーザーに全アラートが送信される（適切だが接続数増加で遅延）

現在の規模では問題なし。接続数が100を超えるとシリアル送信がボトルネックになる可能性。

**対処案**: `asyncio.gather()` で並列送信、またはユーザー別フィルタリング機能の追加。

---

## 3. 拡張性

### ISSUE-078: main.py のルーター登録が手動列挙 [Medium] ✅ 解消済み

**現象**: `main.py:99-114` で15以上のルーターを1行ずつ手動で `include_router()` している。

```python
app.include_router(api_todos.router)
app.include_router(api_attendances.router)
app.include_router(api_attendance_presets.router)
app.include_router(api_tasks.router)
# ... 11行続く
```

**影響**: 新機能追加時に必ず main.py を修正する必要がある。ルーター追加忘れの原因になる。

**解消**: `app/routers/__init__.py` に `all_routers` リストを定義し、`main.py` は1行のループで登録。新ルーター追加は `__init__.py` のリストに追記するだけ。

```python
# app/routers/__init__.py
all_routers: list[APIRouter] = [
    pages.router,
    api_todos.router,
    # ... 全20ルーターを列挙（api_oauth.admin_router 含む）
]

# main.py
from app.routers import all_routers
for _router in all_routers:
    app.include_router(_router)
```

---

### ISSUE-079: WebSocket ハンドラが main.py に3つ重複 [Medium] ✅ 解消済み

**現象**: `main.py:125-170` にログ・アラート・プレゼンスの3つの WebSocket ハンドラが、ほぼ同一の構造で記述されている。

```python
# パターン: accept → auth check → receive loop → disconnect
@app.websocket("/ws/logs")
async def websocket_logs(websocket: WebSocket):
    await log_ws_manager.connect(websocket)
    if not _ws_get_user_id(websocket):
        await websocket.close(code=4401, reason="Not authenticated")
        log_ws_manager.disconnect(websocket)
        return
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        log_ws_manager.disconnect(websocket)

# ↑ 同じパターンが /ws/alerts, /ws/presence にも存在（計3回）
```

**影響**: WebSocket 追加時に同じボイラープレートをコピー。認証ロジック変更時に3箇所を修正する必要がある。

**解消**: `main.py` に `_ws_handler(websocket, manager, name)` を追加し、3ハンドラのボイラープレートを統合。各エンドポイントは1行の委譲呼び出しのみ。

```python
async def _ws_handler(websocket: WebSocket, manager, name: str) -> None:
    """Common WebSocket handler: authenticate, receive loop, disconnect."""
    await manager.connect(websocket)
    if not _ws_get_user_id(websocket):
        await websocket.close(code=4401, reason="Not authenticated")
        manager.disconnect(websocket)
        return
    logger.info("%s WebSocket client connected: %s", name, websocket.client)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        logger.info("%s WebSocket client disconnected: %s", name, websocket.client)

@app.websocket("/ws/logs")
async def websocket_logs(websocket: WebSocket):
    await _ws_handler(websocket, log_ws_manager, "Logs")
# ... 他2つも同様
```

---

### ISSUE-080: ステータス値がマジックストリングで散在 [Medium] ✅ 解消済み

**現象**: 各モデルのステータス値が文字列リテラルとして複数レイヤーに散在し、定数やEnumで定義されていない。

| モデル | ステータス値 | 散在箇所 |
|--------|------------|---------|
| `Task.status` | `"pending"`, `"in_progress"` | models, crud, service, JS |
| `TaskListItem.status` | `"open"`, `"in_progress"`, `"done"` | models, schemas, service, JS |
| `PresenceStatus.status` | `"available"`, `"away"`, `"out"`, `"break"`, `"offline"`, `"meeting"`, `"remote"` | models, schemas, service, JS |
| `Attendance.input_type` | `"web"`, `"ic_card"`, `"admin"` | models, service, JS |
| `Alert.severity` | `"info"`, `"warning"`, `"critical"` | models, schemas, service, JS |
| `User.role` | `"admin"`, `"user"` | models, schemas, deps, service |

**影響**: 新しいステータス値を追加する場合、Python（モデル・スキーマ・サービス）と JavaScript の両方を修正する必要がある。タイプミスによるバグのリスクが高い。

**解消**: `app/core/constants.py` の定数クラスを Python の全レイヤーに適用済み。

- **スキーマ**: `AlertSeverityType`, `PresenceStatusType`, `UserRoleType`, `ItemStatusType` に差し替え
- **サービス**: `presence_service`, `task_list_service`, `task_service`, `attendance_service`, `user_service`, `log_source_service` に適用
- **CRUD**: `crud/task.py` に `TaskStatus` を適用
- **コア**: `core/deps.py` に `UserRole` を適用

> **残課題**: JS 側（フロントエンド）へのマジックストリング対応は未対応（ISSUE-080b として分離）。

---

### ISSUE-081: DEFAULT_CATEGORY_ID が config.py と task_service.py で二重定義 [Low] ✅ 解消済み

**現象**: `app/config.py:45` に `DEFAULT_TASK_CATEGORY_ID = 7` が定義されているが、`task_service.py:20` では独立して `DEFAULT_CATEGORY_ID = 7` を定義。

**解消**: `task_service.py` で `from app.config import DEFAULT_TASK_CATEGORY_ID` に統一済み。独自定義は削除されている。

---

### ISSUE-059: TaskListItem のステータス遷移に制約なし [Medium]

**現象**: `TaskListItemUpdate` スキーマで `status` が直接更新可能。サービスは遷移の妥当性を検証しない。

**問題シナリオ**:
- `open` → `done` に直接変更可能（タスクとして作業せずに完了）
- `done` → `open` に戻し可能（本来 `start_as_task` 経由で `in_progress` にすべき）

**影響**: `total_seconds` が正確に記録されず、ステータスの意味が曖昧になる。

**対処案**: サービス層でステータス遷移の妥当性を検証、または `status` を `TaskListItemUpdate` から除外してアクション経由のみに制限。

---

## 4. モジュール再利用性

### ISSUE-082: CRUD 層に基底クラスがなくコード重複 [High] ✅ 解消済み

**現象**: 19の CRUD ファイルで `get_by_id`, `create`, `update`, `delete` の同一パターンが繰り返されている。

```python
# crud/todo.py
def get_todo(db, todo_id):
    return db.query(Todo).filter(Todo.id == todo_id).first()

# crud/task.py — 同一パターン
def get_task(db, task_id):
    return db.query(Task).filter(Task.id == task_id).first()

# crud/daily_report.py — 同一パターン
def get_report(db, report_id):
    return db.query(DailyReport).filter(DailyReport.id == report_id).first()
```

同様に `create`（`db.add` → `db.commit` → `db.refresh`）、`update`（`setattr` ループ → `commit`）、`delete`（`db.delete` → `commit`）も全ファイルで同一。

**影響**: 全 CRUD への横断的変更（ソフトデリート導入、監査ログ追加等）が19ファイルへの個別修正になる。

**解消**: `app/crud/base.py` に `CRUDBase(Generic[ModelType])` を実装し、以下10ファイルで採用。

- **既存採用済み**: `todo.py`, `task.py`, `daily_report.py`, `task_category.py`, `group.py`, `task_list_item.py`
- **今回移行**: `alert.py`（AlertRule + Alert）, `attendance.py`（get/update/delete）, `log.py`（create）, `log_source.py`（get/update/delete）

`CRUDBase` の設計:
- `get(db, id)` — primary key による単一取得
- `get_all(db)` — 全件取得
- `create(db, data, *, commit=True, **extra_fields)` — Pydantic BaseModel または dict で生成、`extra_fields` で追加カラムを注入（例: `user_id=user_id`, `rule_id=rule_id`）
- `update(db, obj, data, *, commit=True)` — `exclude_unset=True` で部分更新、commit/flush 切り替え対応
- `delete(db, obj, *, commit=True)` — 削除

**残存**: `user.py`（パスワードハッシュ生成を含む特殊 create）、`oauth_provider.py`（ID ベースの update/delete）、`presence.py`（upsert パターン）、`attendance_break.py`、カレンダー系、認証系ログは専用ロジックが多く対象外。

---

### ISSUE-083: サービス層の戻り値型が不統一 [Medium] ✅ 解消済み

**現象**: サービスによって ORM モデルを返すものと dict を返すものが混在。

| サービス | 戻り値 | 例 |
|---------|--------|-----|
| `todo_service` | `Todo`（ORM モデル） | `create_todo() -> Todo` |
| `task_service` | `Task`（ORM モデル） | `create_task() -> Task` |
| `daily_report_service` | `DailyReport`（ORM モデル） | `create_report() -> DailyReport` |
| **`attendance_service`** | **`dict`** | `clock_in() -> dict` |
| `alert_service` | `Alert`（ORM モデル、async） | `async create_alert() -> Alert` |
| `presence_service` | `list[dict]` / `PresenceStatusWithUser` | 混在 |

さらに一部サービスが `async def` で、残りは `def`（同期）。

```python
# attendance_service.py — dict を返す
def clock_in(db, user_id, note=None) -> dict:
    result = crud_att.clock_in(db, user_id, note)
    return _attach_breaks(db, result)  # dict 変換

# alert_service.py — async で ORM を返す
async def create_alert(db, data) -> Alert:
```

**影響**: 新サービス作成時にどちらのパターンに合わせるべきか不明瞭。ルーター層での処理が統一できない。

**対処案**:
- 原則: ORM モデルを返し、ルーター/スキーマ層で変換
- `attendance_service` の dict 返却は breaks リレーション不足が原因 → ORM リレーション追加で解消可能
- async/sync の統一方針を決定

**解消**:
- **async/sync 統一**: `alert_service.py` の11関数（`create_alert`, `evaluate_rules_for_log` 等）を `async def` → `def` に変換
- **dict→ORM**: `attendance_service.py` を全面リファクタリング
  - `Attendance` モデルに `breaks = relationship(..., lazy="selectin", cascade="all, delete-orphan")` を追加
  - `_attach_breaks()` 関数を削除し、全10関数の戻り値を `dict` → `Attendance` ORM モデルに変更
  - `get_status()` の戻り値を `AttendanceStatusResult` dataclass（`is_clocked_in`, `current_attendance` フィールド）に変更
  - `generate_monthly_excel()` 内の `rec["key"]` アクセスを `rec.attr` に更新
  - `get_status` ルーターハンドラを dict アクセス → dataclass 属性アクセスに更新
- 副次効果: ISSUE-072 (N+1) も同時解消（selectin ローダーで 23クエリ → 2クエリ）

---

### ISSUE-084: `_parse_time()` が2サービスで重複 [Medium] ✅ 解消済み

**現象**: HH:MM 文字列 + date → UTC datetime の変換関数が2箇所に存在。

```python
# attendance_service.py:22-30
def _parse_time(target_date: date, time_str: str) -> datetime:
    t = time.fromisoformat(time_str)
    local_dt = datetime.combine(target_date, t)
    return local_dt.astimezone(timezone.utc)

# task_service.py:134-142
def _parse_local_time(target_date: date, time_str: str) -> datetime:
    t = time.fromisoformat(time_str)
    local_dt = datetime.combine(target_date, t)
    return local_dt.astimezone(timezone.utc)
```

名前が異なるだけで処理は完全に同一。

**影響**: タイムゾーン処理の修正時に2箇所を同時に修正する必要がある。

**対処案**: `app/core/utils.py` に共通関数として切り出し。

**解消**: `app/core/utils.py` に `parse_hhmm_to_utc(target_date, time_str)` として定義。両サービスから `from app.core.utils import parse_hhmm_to_utc` でインポートし、個別の実装を削除。

---

### ISSUE-058: JS カテゴリマッピングが3ファイルで重複 [Low] ✅ 解消済み

**現象**: `tasks.js`, `task_list.js`, `reports.js` で同じパターンのカテゴリマスタ取得・マッピングロジックが独立実装。

**対処案**: `common.js` に共通ユーティリティとして切り出す。

```javascript
let _categoryCache = null;
async function getCategoryMap() {
    if (!_categoryCache) {
        const cats = await api.get('/api/task-categories/');
        _categoryCache = Object.fromEntries(cats.map(c => [c.id, c.name]));
    }
    return _categoryCache;
}
```

**解消**: `common.js` に `getCategories()` を追加（配列キャッシュ）。各 `loadCategories()` の `api.get('/api/task-categories/')` を `getCategories()` に置換。DOM 操作はページ固有のため変更なし。

---

### ISSUE-085: WebSocketManager にユーザー単位の制御機能なし [Low]

**現象**: `websocket_manager.py` の `WebSocketManager` は接続リストのみを管理し、接続元ユーザー情報を保持しない。

```python
class WebSocketManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []  # ユーザー情報なし

    async def broadcast(self, data: dict):
        for connection in self.active_connections[:]:
            await connection.send_json(data)  # 全員に送信
```

**影響**: 以下の機能拡張ができない:
- 特定ユーザーにのみメッセージ送信（例: 自分宛のアラートのみ通知）
- ユーザー別の接続数制限
- 接続中ユーザー一覧の取得

**対処案**: 接続時にユーザー ID を紐付ける拡張。

```python
class WebSocketManager:
    def __init__(self):
        self.connections: Dict[int, List[WebSocket]] = defaultdict(list)

    async def connect(self, websocket: WebSocket, user_id: int): ...
    async def send_to_user(self, user_id: int, data: dict): ...
    async def broadcast(self, data: dict): ...
```

---

## 5. その他（既存課題の継続）

### ISSUE-056: task_list.js の Backlog URL がハードコード [Low] ✅ 解消済み

**現象**: `tasks.js` と `presence.js` は `window.__backlogSpace` 対応済みだが、`task_list.js` にハードコードが残存。

**対処案**: `window.__backlogSpace || 'ottsystems'` を使用。

**解消**: `task_list.js` の Backlog URL を `https://${escapeHtml(window.__backlogSpace || 'ottsystems')}.backlog.com/...` に変更。

---

### ISSUE-057: JavaScript にデバッグ用 console.log が残存 [Low] ✅ 解消済み

**現象**: `attendance.js`（8箇所）、`tasks.js`（1箇所）、`common.js`（1箇所）にデバッグログ残存。

**対処案**: 不要な `console.log` を削除。

**解消**: `attendance.js` 6箇所・`common.js` 1箇所を削除。`tasks.js` の `console.log` は既に除去済みで `console.error`（エラーハンドリング）のみ残存（削除対象外）。

---

### ISSUE-060: Presence サービスの3クエリ構造 [Low]

**現象**: `presence_service.py` の `get_all_statuses()` が3つの独立クエリ（全ステータス、全ユーザー、全タスク）を実行しメモリ上で結合。

**対処案**: JOIN クエリへの統合。

---

## まとめ

### 重要度別件数

| 重要度 | 件数 | Issue番号 |
|--------|------|-----------|
| Critical | 0 | — |
| High | 1 | 063 |
| Medium | 4 | 059, 069, 074, 076 |
| Low | 5 | 060, 070, 071, 077, 085 |
| **合計（残存）** | **10** | |
| ✅ 解消済み | 19 | 053, 054, 055, 056, 057, 058, 065, 066, 067, 068, 072, 075, 078, 079, 080, 081, 082, 083, 084 |

### カテゴリ別件数

| カテゴリ | 残存件数 | 残存Issue番号 | 解消済み |
|---------|---------|-------------|---------|
| セキュリティ | 3 | 069, 070, 071 | ~~053, 054, 055, 065, 066, 067, 068~~ |
| 性能 | 4 | 063, 074, 076, 077 | ~~072, 075~~ |
| 拡張性 | 1 | 059 | ~~078, 079, 080, 081~~ |
| 再利用性 | 1 | 085 | ~~058, 082, 083, 084~~ |

### 優先度付きアクション

#### 即時対応推奨

| # | Issue | 内容 | 工数 |
|---|-------|------|------|
| ~~1~~ | ~~**065**~~ | ~~SECRET_KEY デフォルト値の強化~~ | ~~解消済み~~ |
| ~~2~~ | ~~**053**~~ | ~~role フィールドを `Literal` に制約~~ | ~~解消済み~~ |
| ~~3~~ | ~~**084**~~ | ~~`_parse_time` を共通モジュールに切り出し~~ | ~~解消済み~~ |
| ~~4~~ | ~~**081**~~ | ~~DEFAULT_CATEGORY_ID を config.py から import~~ | ~~解消済み~~ |
| ~~5~~ | ~~**067**~~ | ~~create_item の parent_id 権限チェック追加~~ | ~~該当なし~~ |

#### 計画的に対応

| # | Issue | 内容 | 工数 |
|---|-------|------|------|
| 6 | **063** | FK カラムへのインデックス一括追加 | 中（マイグレーション） |
| ~~7~~ | ~~**072**~~ | ~~attendance の N+1 クエリ解消~~ | ~~解消済み（ISSUE-083 の副次効果）~~ |
| ~~8~~ | ~~**082**~~ | ~~CRUD 基底クラスの導入~~ | ~~解消済み~~ |
| ~~9~~ | ~~**080**~~ | ~~Python 層のステータス値定数化~~ | ~~解消済み（JS 層は残存）~~ |
| 10 | **069** | 公開ログ API のバリデーション強化 | 中 |

#### 将来対応（低優先度）

| # | Issue | 内容 |
|---|-------|------|
| 11 | 074 | アラートルール評価のキャッシュ化 |
| ~~12~~ | ~~075~~ | ~~サマリー集計の単一パス化~~ | ~~解消済み（DB レベル最適化は残存課題として記録）~~ |
| 13 | 076 | ページネーション導入 |
| ~~14~~ | ~~078~~ | ~~main.py のルーター登録整理~~ |
| ~~15~~ | ~~083~~ | ~~サービス層の戻り値型統一~~ |
| 16 | 085 | WebSocketManager のユーザー対応拡張 |
