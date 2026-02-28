# スキルノート — パフォーマンス改善・設計知識の蓄積

> このドキュメントは開発作業を通じて学んだ知識・パターン・落とし穴をまとめたものです。
> ISSUE の修正・レビューなどを通じて得た教訓を記録し、今後の開発に活かします。

---

## 1. SQLAlchemy: N+1 クエリの識別と解消

### 1.1 N+1 クエリとは

「1 件ずつ取得するクエリが N 回繰り返される」パターン。

```python
# NG: N+1 パターン
sources = crud_log_source.get_log_sources(db)       # Query 1
for source in sources:
    paths = crud_path.get_paths_by_source(db, s.id) # Query N（ソース数分）
```

```python
# OK: バッチ取得パターン
sources = crud_log_source.get_log_sources(db)                           # Query 1
source_ids = [s.id for s in sources]
paths_map = crud_path.get_paths_by_source_ids(db, source_ids)           # Query 1
# paths_map.get(source.id, []) でループ内 O(1) アクセス
```

### 1.2 発見のポイント

- `for item in list:` の中に `crud_xxx.get_xxx(db, item.id)` があれば N+1 の可能性が高い
- 既に他の関数でバッチ取得が実装済みのケースが多い（`list_source_statuses` が先に最適化されていたが `list_sources` は未対応だった例）
- `_to_response_dict` や `_to_xxx_response` などのヘルパー関数内でクエリが発行されていると、呼び出し側のループで N+1 になりやすい

### 1.3 バッチ CRUD 関数の命名規則

| シングル取得 | バッチ取得 | 戻り値 |
|------------|---------|-------|
| `get_xxx_by_source(db, source_id)` | `get_xxx_by_source_ids(db, source_ids)` | `Dict[int, List[T]]` |
| `get_xxx(db, id)` | `get_xxxs_by_ids(db, ids)` | `List[T]` |
| `count_xxx_by_group(db, group_id)` | `count_xxx_all_groups(db)` | `Dict[Optional[int], int]` |
| `get_active_entry(db, task_id)` | `get_active_entries_batch(db, task_ids)` | `Dict[int, T]` |

### 1.4 集計クエリ（GROUP BY）のバッチ化

```python
# NG: グループごとに COUNT クエリ
for group in groups:
    link_count = crud.count_links_by_group(db, group.id)  # N クエリ

# OK: 1回の GROUP BY
def count_links_all_groups(db: Session) -> Dict[Optional[int], int]:
    rows = db.query(SiteLink.group_id, func.count(SiteLink.id)).group_by(SiteLink.group_id).all()
    return {gid: cnt for gid, cnt in rows}

counts_map = crud.count_links_all_groups(db)  # 1クエリ
for group in groups:
    link_count = counts_map.get(group.id, 0)  # O(1) アクセス
```

---

## 2. SQLAlchemy: Python フィルタ vs SQL フィルタ

### 2.1 アンチパターン: 全件取得 + Python 絞り込み

```python
# NG: 全件取得して Python でフィルタ
paths = crud_path.get_paths_by_source(db, source.id)
enabled_paths = [p for p in paths if p.is_enabled]  # Python 側フィルタ

users = crud_user.get_users(db, active_only=True)    # 全ユーザー
if group_id is not None:
    users = [u for u in users if u.group_id == group_id]  # Python フィルタ
```

```python
# OK: SQL WHERE でフィルタ
enabled_paths = crud_path.get_enabled_paths_by_source(db, source.id)  # WHERE is_enabled=true

users = crud_user.get_users_in_group(db, group_id, active_only=True)   # WHERE group_id=:id
```

### 2.2 確認するポイント

既存 CRUD に条件付き取得関数が実装済みかを確認する。
`get_enabled_paths_by_source` のように既に存在するが使われていないケースが典型例。

---

## 3. SQLAlchemy: `lazy="joined"` の確認

N+1 と疑う前に、**モデルのリレーション定義を確認する**。

```python
# app/models/site_link.py の例
class SiteLink(Base):
    group = relationship("SiteGroup", back_populates="links", lazy="joined")
    # lazy="joined" → JOIN 済みなので link.group アクセスで追加クエリは発生しない
```

`lazy="joined"` が設定されていれば、そのリレーションへのアクセスは N+1 にならない。
誤って `joinedload` を追加すると二重結合になるため注意。

---

## 4. Pydantic v2: `model_validate(orm_obj)` の活用

`from_attributes = True`（旧: `orm_mode = True`）が設定されたスキーマは ORM オブジェクトを直接渡せる。

```python
# NG: 手動でカラムをイテレート
def _to_link_response(link: SiteLink) -> SiteLinkResponse:
    data = {col.name: getattr(link, col.name) for col in link.__table__.columns if col.name != "url"}
    data["group_name"] = group_name
    return SiteLinkResponse.model_validate(data)

# OK: ORM オブジェクトを直接渡す
def _to_link_response(link: SiteLink) -> SiteLinkResponse:
    response = SiteLinkResponse.model_validate(link)  # from_attributes=True が必要
    response.group_name = link.group.name if link.group else None
    return response
```

**注意点:**
- スキーマに存在しないカラム（`url` など）は自動的に無視される
- `Optional` フィールドはデフォルト `None` になるため、後から代入しても問題ない
- `model_validate` 後のフィールド変更は `model_config = {"frozen": False}` が必要（デフォルトは mutable）

---

## 5. Python: 正規表現のキャッシュ

### 5.1 問題

`re.match(pattern_str, text)` は毎回パターンをコンパイルする（Python 内部キャッシュはサイズ512で LRU だが明示的ではない）。

### 5.2 `functools.lru_cache` によるキャッシュ

```python
import functools, re

@functools.lru_cache(maxsize=32)
def _compile_pattern(pattern: str) -> re.Pattern:
    return re.compile(pattern)

# ループ内での使用
for line in lines:
    compiled = _compile_pattern(source.parser_pattern)  # 同パターンはキャッシュを返す
    m = compiled.match(line)
```

**適用場面:** ログ行のパースのようにループ内で同じパターンを繰り返し使う場合。

---

## 6. Python: ループ内の不変オブジェクト生成

### 6.1 アンチパターン

```python
# NG: ループのたびに新しい dict を生成
for source in sources:
    _empty = {"total": 0, "new": 0, "updated": 0, "unchanged": 0}  # 毎回生成
    counts = counts_map.get(source.id, _empty)
```

### 6.2 モジュールレベル定数化

```python
# OK: モジュールレベルで1回だけ生成
_EMPTY_FILE_COUNTS: Dict[str, int] = {
    "total": 0, "new": 0, "updated": 0, "unchanged": 0, "deleted": 0, "error": 0,
}

for source in sources:
    counts = counts_map.get(source.id, _EMPTY_FILE_COUNTS)  # 同じオブジェクトを参照
```

**注意:** `dict.get(key, default)` の `default` は読み取り専用用途なら共有で問題ない（変更しないこと）。

---

## 7. Python: lazy import（関数内 import）の適否

### 7.1 循環 import 回避のための lazy import

```python
# 意図的なケース: 循環 import を防ぐために関数内で import
def scan_source(...):
    from app.constants import AlertSeverity  # 循環回避
    from app.crud import alert as crud_alert
```

### 7.2 不要な lazy import

```python
# NG: 循環 import がないのに関数内で import
def get_logs(db, user_id):
    from app.config import API_PRESENCE_LOG_LIMIT  # 不要
    return crud_presence.get_presence_logs(db, user_id, API_PRESENCE_LOG_LIMIT)

# OK: モジュールレベルに移動
from app.config import API_PRESENCE_LOG_LIMIT

def get_logs(db, user_id):
    return crud_presence.get_presence_logs(db, user_id, API_PRESENCE_LOG_LIMIT)
```

**判断基準:** 循環 import が発生するか否かを確認した上で、発生しないなら必ずモジュールレベルに移動する。

---

## 8. バッチ処理のパターン: `batch_done` の最適化事例

### 8.1 Before（N+1 パターン）

```python
for item in items:
    task = crud_task.get_task(db, item.task_id)         # クエリ N
    active = crud_task.get_active_entry(db, task.id)    # クエリ N
    ...
    source_item = crud_tli.get_item(db, source_item_id) # クエリ N
    source_item.total_seconds += accumulated_seconds
```

### 8.2 After（バッチ取得 + dict 蓄積）

```python
# 1. バッチ取得（ループ前に1回）
task_ids = [item.task_id for item in items]
task_map = {t.id: t for t in crud_task.get_tasks_by_ids(db, task_ids)}    # 1クエリ
active_entries = crud_task.get_active_entries_batch(db, task_ids)           # 1クエリ

# 2. ループ内は dict アクセスのみ
for item in items:
    task = task_map[item.task_id]                        # O(1), no DB
    if task.id in active_entries:                        # O(1), no DB
        crud_task.stop_timer_at(db, task, end_time_utc)

    # 3. 集計を dict に蓄積（DB 書き込みを後回し）
    if source_item_id and accumulated_seconds > 0:
        accumulated_by_source[source_item_id] = (
            accumulated_by_source.get(source_item_id, 0) + accumulated_seconds
        )

# 4. バッチ更新（ループ後に1回）
if accumulated_by_source:
    source_items = crud_tli.get_items_by_ids(db, list(accumulated_by_source.keys()))  # 1クエリ
    for si in source_items.values():
        si.total_seconds += accumulated_by_source[si.id]
    db.flush()
```

**ポイント:**
1. 所有権チェック（`user_id` 検証）をループ前に行う → DB 書き込み前にまとめて検証
2. 更新量を dict に蓄積してからバッチ適用 → ループ内の `get` + `update` を排除
3. `db.flush()` で部分コミットを避けつつ ID を確定させる
4. 最後に1回 `db.commit()`

---

## 9. portal_core 分離に関する注意点

### 9.1 portal_core を変更せずに拡張する

`portal_core` は共通基盤。アプリ固有の関数は `app/` 側の shim ファイルに追加する。

```python
# app/crud/user.py（shim）
# portal_core.crud.user に group_id フィルタを追加せず、app 側で定義
def get_users_in_group(db: Session, group_id: int, active_only: bool = False) -> List[User]:
    q = db.query(User).filter(User.group_id == group_id)
    if active_only:
        q = q.filter(User.is_active.is_(True))
    return q.all()
```

### 9.2 `mock.patch` のターゲット

shim の `app.xxx` ではなく実体の `portal_core.xxx` をパッチする。

```python
# NG
@mock.patch("app.services.auth_service.hash_password")
# OK
@mock.patch("portal_core.core.security.hash_password")
```

---

## 10. コードレビューチェックリスト（パフォーマンス観点）

新しい機能を実装・レビューする際の確認項目:

- [ ] ループ内に `db.query` や `crud.get_xxx` が含まれていないか？（N+1 の疑い）
- [ ] `_to_response_dict` / `_to_xxx_response` のような変換関数内でクエリが発行されていないか？
- [ ] 全件取得後に Python 側でフィルタリングしていないか？ SQL の `WHERE` 句で絞り込めるか？
- [ ] 新しく作る `count_xxx_by_id` 系の関数は GROUP BY でまとめられないか？
- [ ] ループ内で毎回生成している不変オブジェクト（dict, list）をモジュールレベルに出せないか？
- [ ] 関数内 `import` は循環 import 回避のための意図的なものか？
- [ ] ORM のリレーション `lazy` 設定を確認してから N+1 対策を検討する
- [ ] Pydantic スキーマに `from_attributes = True` が設定されているなら `model_validate(orm_obj)` を使えないか？
