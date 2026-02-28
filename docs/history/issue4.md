# ISSUE-4: 重複処理・不要な処理・非効率な処理

作成日: 2026-02-25

---

## 概要

コードベース全体をレビューし、以下の観点で問題を抽出した。

- **重複処理**: 同じデータを複数回クエリ・計算する処理
- **不要な処理**: 結果が使われない、または SQL 側で処理できるのに Python 側でやっている処理
- **非効率な処理**: アルゴリズム的に改善できる処理
- **低性能な処理**: N+1 クエリ、インデックス不足など DB アクセスのボトルネック

---

## 問題一覧

### ISSUE-4-01 【高】N+1 クエリ: `list_sources` でパス情報を1件ずつ取得

**カテゴリ**: 低性能な処理（N+1 クエリ）
**影響度**: 高（ログソース数に比例してクエリが増加）

**ファイル**: [app/services/log_source_service.py](app/services/log_source_service.py)

**問題のコード**:
```python
# line 216-219
def list_sources(db: Session) -> List[dict]:
    sources = crud_log_source.get_log_sources(db)       # Query 1: ソース一覧
    group_map = _build_group_map(db)                     # Query 2: グループ一覧
    return [_to_response_dict(db, s, group_map=group_map) for s in sources]  # Query N: パス一覧

# line 769-789 (_to_response_dict の中)
def _to_response_dict(db: Session, source: LogSource, group_map=None) -> dict:
    paths = crud_path.get_paths_by_source(db, source.id)  # ← ここが1ソースごとに1クエリ
    ...
```

**詳細**:
- ソースが N 件ある場合、合計 N+2 クエリが発行される
- `list_source_statuses` では既に `get_paths_by_source_ids`（バッチ取得）を使って改善済みだが、`list_sources` は未対応

**修正方針**:
- ソース ID リストを収集後、`get_paths_by_source_ids(db, source_ids)` で一括取得してから `_to_response_dict` に渡す
- `list_source_statuses` の実装パターンを参照

---

### ISSUE-4-02 【高】N+1 クエリ: `list_groups` でグループごとにリンク数をカウント

**カテゴリ**: 低性能な処理（N+1 クエリ）
**影響度**: 高（サイトグループ数に比例してクエリが増加）

**ファイル**: [app/services/site_link_service.py](app/services/site_link_service.py)

**問題のコード**:
```python
# line 40-50
def _to_group_response(group: SiteGroup, db: Session) -> SiteGroupResponse:
    link_count = crud.count_links_by_group(db, group.id)  # ← グループごとに COUNT クエリ
    return SiteGroupResponse(..., link_count=link_count)

# line 63-65
def list_groups(db: Session) -> List[SiteGroupResponse]:
    groups = crud.get_groups(db)                              # Query 1
    return [_to_group_response(g, db) for g in groups]       # Query N（グループ数分）
```

**CRUD 実装** ([app/crud/site_link.py](app/crud/site_link.py) line 54-55):
```python
def count_links_by_group(db: Session, group_id: int) -> int:
    return db.query(func.count(SiteLink.id)).filter(SiteLink.group_id == group_id).scalar() or 0
```

**詳細**:
- グループが 10 件ある場合、11 クエリ（1 + 10 COUNT）が発行される

**修正方針**:
- `GROUP BY` 集計クエリを1回実行して全グループのカウントを取得する
```python
# CRUD に追加する関数例
def count_links_all_groups(db: Session) -> dict:
    rows = db.query(SiteLink.group_id, func.count(SiteLink.id)).group_by(SiteLink.group_id).all()
    return {group_id: count for group_id, count in rows}
```

---

### ISSUE-4-03 【高】N+1 クエリ: `scan_source` で変更ファイルをパスごとに個別取得

**カテゴリ**: 低性能な処理（N+1 クエリ）
**影響度**: 高（監視パス数に比例してクエリが増加）

**ファイル**: [app/services/log_source_service.py](app/services/log_source_service.py)

**問題のコード**:
```python
# line 575-581
if source.alert_on_change and (total_new > 0 or total_updated > 0):
    for p in enabled_paths:
        changed_files = crud_log_file.get_changed_files_by_path(db, p.id)  # ← パスごとに1クエリ
        for log_file in changed_files:
            ...
```

**詳細**:
- `list_source_statuses` では `get_changed_files_by_path_ids`（バッチ取得）を使って改善済み
- `scan_source` の同フェーズは未対応

**修正方針**:
```python
# enabled_paths の ID を収集
enabled_path_ids = [p.id for p in enabled_paths]
# バッチ取得
changed_files_map = crud_log_file.get_changed_files_by_path_ids(db, enabled_path_ids)
# ループ内では dict から取得
for p in enabled_paths:
    changed_files = changed_files_map.get(p.id, [])
```

---

### ISSUE-4-04 【中】正規表現の毎回コンパイル: `_parse_log_line`

**カテゴリ**: 非効率な処理
**影響度**: 中（ログ行数に比例してオーバーヘッドが増加）

**ファイル**: [app/services/log_source_service.py](app/services/log_source_service.py)

**問題のコード**:
```python
# line 95-110
def _parse_log_line(line, parser_pattern, severity_field, default_severity):
    if parser_pattern and severity_field:
        m = re.match(parser_pattern, line)  # ← 毎回 pattern を文字列からコンパイル

# line 148-151 (ループ内で呼び出される)
for i, line in enumerate(lines):
    parsed = _parse_log_line(line, source.parser_pattern, ...)
```

**詳細**:
- `re.match(pattern_str, line)` は `re.compile(pattern_str).match(line)` と等価
- Python は `re` モジュールのキャッシュ（サイズ512）でコンパイル済みパターンをキャッシュしているが、`functools.lru_cache` とは異なり、キャッシュが一杯になると古いものが削除される
- 1000 行のファイルで同じパターンを使う場合、キャッシュが効いていれば問題は少ないが、明示的なコンパイルにすることでキャッシュ依存をなくせる

**修正方針**:
- ループの呼び出し側で `compiled_pattern = re.compile(source.parser_pattern)` してから引数で渡す
```python
compiled = re.compile(source.parser_pattern) if source.parser_pattern else None
for i, line in enumerate(lines):
    parsed = _parse_log_line(line, compiled, source.severity_field, source.default_severity)
```

---

### ISSUE-4-05 【中】N+1 クエリ: `list_links` で `link.group` を遅延ロード

**カテゴリ**: 低性能な処理（N+1 クエリ / 遅延ロード）
**影響度**: 中（サイトリンク数に比例してクエリが増加）

**ファイル**: [app/services/site_link_service.py](app/services/site_link_service.py), [app/crud/site_link.py](app/crud/site_link.py)

**問題のコード**:
```python
# site_link_service.py line 53-54
def _to_link_response(link: SiteLink) -> SiteLinkResponse:
    group_name = link.group.name if link.group else None  # ← 遅延ロードが発生
```

```python
# crud/site_link.py line 61-67
def get_links(db: Session) -> List[SiteLink]:
    return (
        db.query(SiteLink)
        .filter(SiteLink.is_enabled == True)
        .order_by(...)
        .all()
    )  # joinedload なし → link.group アクセスで N 回の追加クエリ
```

**詳細**:
- リンクが 20 件ある場合、最大 21 クエリ（1 + 20 遅延ロード）が発行される

**修正方針**:
```python
# crud/site_link.py
from sqlalchemy.orm import joinedload

def get_links(db: Session) -> List[SiteLink]:
    return (
        db.query(SiteLink)
        .options(joinedload(SiteLink.group))  # 追加
        .filter(SiteLink.is_enabled == True)
        .order_by(...)
        .all()
    )
```

---

### ISSUE-4-06 【中】Python 側での in-memory フィルタリング: `scan_source` のパスフィルタ

**カテゴリ**: 不要な処理
**影響度**: 中（全パスを取得してから有効パスのみ使用）

**ファイル**: [app/services/log_source_service.py](app/services/log_source_service.py)

**問題のコード**:
```python
# line 461-462
paths = crud_path.get_paths_by_source(db, source.id)          # 全パスを取得
enabled_paths = [p for p in paths if p.is_enabled]           # Python でフィルタ
```

**修正方針**:
- CRUD に `get_enabled_paths_by_source(db, source_id)` を追加して SQL `WHERE is_enabled = true` でフィルタリング

---

### ISSUE-4-07 【中】Python 側での in-memory フィルタリング: `get_summary` のグループフィルタ

**カテゴリ**: 不要な処理
**影響度**: 中（全ユーザー・全日報を取得してから Python 側でフィルタ）

**ファイル**: [app/services/summary_service.py](app/services/summary_service.py)

**問題のコード**:
```python
# line 53-62
all_reports = crud_report.get_reports_by_date_range(db, period_start, period_end)  # 全日報取得
users = crud_user.get_users(db, active_only=True)                                   # 全ユーザー取得

if group_id is not None:
    users = [u for u in users if u.group_id == group_id]          # Python フィルタ
    target_user_ids = {u.id for u in users}
    reports = [r for r in all_reports if r.user_id in target_user_ids]  # Python フィルタ
```

**詳細**:
- `group_id` が指定された場合でも全データを取得してから絞り込む
- データ量が多い場合に無駄な転送が発生

**修正方針**:
- `get_users` に `group_id` パラメータを追加して SQL `WHERE group_id = :group_id` でフィルタリング
- `get_reports_by_date_range` に `user_ids` パラメータを追加して `WHERE user_id IN (...)` でフィルタリング

---

### ISSUE-4-08 【中】`_empty` ディクショナリをループ内で毎回生成

**カテゴリ**: 非効率な処理
**影響度**: 低〜中（ソース数分のオブジェクト生成）

**ファイル**: [app/services/log_source_service.py](app/services/log_source_service.py)

**問題のコード**:
```python
# line 384-387
for source in sources:
    _empty = {"total": 0, "new": 0, "updated": 0, "unchanged": 0, "deleted": 0, "error": 0}
    counts = counts_map.get(source.id, _empty)
```

**詳細**:
- `_empty` ディクショナリがループのたびに新しいオブジェクトとして生成される

**修正方針**:
- ループの外側でモジュールレベル定数として定義する
```python
_EMPTY_COUNTS = {"total": 0, "new": 0, "updated": 0, "unchanged": 0, "deleted": 0, "error": 0}

for source in sources:
    counts = counts_map.get(source.id, _EMPTY_COUNTS)  # イミュータブルに注意（get のデフォルトなら OK）
```

---

### ISSUE-4-09 【中】`batch_done` でタスクを1件ずつ取得

**カテゴリ**: 低性能な処理（N+1 クエリ）
**影響度**: 中（バッチ処理のタスク数に比例）

**ファイル**: [app/services/task_service.py](app/services/task_service.py)

**問題のコード**:
```python
# line 205-214
for item in items:
    task = crud_task.get_task(db, item.task_id)   # ← アイテムごとに1クエリ
    ...
    active = crud_task.get_active_entry(db, task.id)  # ← さらに1クエリ
```

**修正方針**:
- ループ前に全タスク ID を収集して一括取得
```python
task_ids = [item.task_id for item in items]
tasks = {t.id: t for t in crud_task.get_tasks_by_ids(db, user_id, task_ids)}
```

---

### ISSUE-4-10 【低】`_to_link_response` でテーブル列を全件イテレート

**カテゴリ**: 非効率な処理
**影響度**: 低（レスポンス生成のたびに余分なオーバーヘッド）

**ファイル**: [app/services/site_link_service.py](app/services/site_link_service.py)

**問題のコード**:
```python
# line 53-57
def _to_link_response(link: SiteLink) -> SiteLinkResponse:
    group_name = link.group.name if link.group else None
    data = {col.name: getattr(link, col.name) for col in link.__table__.columns if col.name != "url"}
    data["group_name"] = group_name
    return SiteLinkResponse.model_validate(data)
```

**詳細**:
- `link.__table__.columns` でテーブルのメタデータをイテレートし、毎回 `if col.name != "url"` のチェックを行う
- `SiteLinkResponse` の `from_attributes = True` を利用することで直接モデルから変換できる

**修正方針**:
- Pydantic の `from_attributes = True` が既に設定されているので `model_validate(link)` が使えるが、`url` フィールドを除外する必要がある
- または明示的なフィールドマッピング関数に変更する

---

### ISSUE-4-11 【低】`presence_service.get_logs` の関数内 lazy import

**カテゴリ**: 不要な処理
**影響度**: 低（呼び出しごとに import のオーバーヘッド）

**ファイル**: [app/services/presence_service.py](app/services/presence_service.py)

**問題のコード**:
```python
# line 62-64
def get_logs(db: Session, user_id: int):
    from app.config import API_PRESENCE_LOG_LIMIT   # ← 関数内 import
    return crud_presence.get_presence_logs(db, user_id, API_PRESENCE_LOG_LIMIT)
```

**修正方針**:
- モジュールレベルの import に移動する（循環 import がない場合）

---

## 優先度まとめ・対応状況

修正日: 2026-02-25

| ID | 問題 | カテゴリ | 影響度 | 対応優先度 | 状態 |
|----|------|----------|--------|-----------|------|
| ISSUE-4-01 | `list_sources` パス N+1 | 低性能（N+1） | 高 | P1 | ✅ 修正済 |
| ISSUE-4-02 | `list_groups` COUNT N+1 | 低性能（N+1） | 高 | P1 | ✅ 修正済 |
| ISSUE-4-03 | `scan_source` 変更ファイル N+1 | 低性能（N+1） | 高 | P1 | ✅ 修正済 |
| ISSUE-4-04 | 正規表現の毎回コンパイル | 非効率 | 中 | P2 | ✅ 修正済 |
| ISSUE-4-05 | `list_links` 遅延ロード N+1 | 低性能（N+1） | 中 | P2 | ⚠️ 対応不要（後述） |
| ISSUE-4-06 | `scan_source` パスの in-memory フィルタ | 不要な処理 | 中 | P2 | ✅ 修正済 |
| ISSUE-4-07 | `get_summary` グループの in-memory フィルタ | 不要な処理 | 中 | P2 | ✅ 修正済 |
| ISSUE-4-08 | `_empty` 毎回生成 | 非効率 | 低 | P3 | ✅ 修正済 |
| ISSUE-4-09 | `batch_done` タスク N+1 | 低性能（N+1） | 中 | P2 | ✅ 修正済 |
| ISSUE-4-10 | `_to_link_response` 列イテレート | 非効率 | 低 | P3 | ✅ 修正済 |
| ISSUE-4-11 | 関数内 lazy import | 不要な処理 | 低 | P3 | ✅ 修正済 |

### ISSUE-4-05 について（対応不要と判断）

調査の結果、`SiteLink.group` リレーションシップに `lazy="joined"` が設定済みであることを確認した（`app/models/site_link.py`）。
このため `link.group` アクセスで追加クエリは発生しない（JOIN 済み）。実際の N+1 は存在しないため対応不要と判断。

---

## 修正サマリー（対応内容）

### 修正ファイル一覧

| ファイル | 対応 ISSUE |
|---------|-----------|
| `app/crud/task.py` | 4-09: `get_tasks_by_ids`, `get_active_entries_batch` 追加 |
| `app/crud/task_list_item.py` | 4-09: `get_items_by_ids` 追加 |
| `app/crud/site_link.py` | 4-02: `count_links_all_groups` 追加 |
| `app/crud/daily_report.py` | 4-07: `user_ids` フィルタ追加 |
| `app/crud/user.py` | 4-07: `get_users_in_group` 追加（shimとして portal_core は変更せず） |
| `app/services/log_source_service.py` | 4-01, 4-03, 4-04, 4-06, 4-08 |
| `app/services/site_link_service.py` | 4-02, 4-10 |
| `app/services/summary_service.py` | 4-07 |
| `app/services/task_service.py` | 4-09 |
| `app/services/presence_service.py` | 4-11 |

### 検証結果

```
ruff check --fix . && ruff format .  → All checks passed
portal_core: 151/151 passed
app:         553/553 passed
```

---

## 参考: 既に最適化済みの箇所

以下の箇所は既にバッチ取得・一括処理が実装されており、参考になる。

- `list_source_statuses`（log_source_service.py）: `get_paths_by_source_ids`、`count_files_all_sources`、`get_changed_files_by_path_ids` で3クエリに集約済み
- `scan_source` の既存ファイル取得（line 532）: `get_files_by_path` で1パスあたり1クエリ（ファイルごとではない）
- `get_all_statuses`（presence_service.py）: 3クエリで全データ取得後、Python 側で dict を使って O(1) ルックアップ
- `summary_service.get_summary`（line 84-98）: 単一ループで全集計を同時に実行（single-pass aggregation）
