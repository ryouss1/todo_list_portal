# ISSUE2: ソースコード 課題一覧

> 作成日: 2026-02-25
> 対象バージョン: Alembic head `c3d4e5f6a7b8` (wiki_content_to_markdown)

---

## 概要

現時点のソースコードについて、セキュリティ・アーキテクチャ・パフォーマンス・保守性の観点から発見された課題をまとめる。

---

## 課題一覧

### ISSUE-2-01: Wiki ページツリー・一覧が visibility フィルタなしで全件返却

**発見箇所:** `app/routers/api_wiki.py:106-111`, `app/services/wiki_service.py:228-251`
**優先度:** 高（セキュリティ）
**状態:** ✅ 解決済み（2026-02-25）

**内容:**
`GET /api/wiki/pages/tree` および `GET /api/wiki/pages/` の2エンドポイントが `visibility=private` のページを認可チェックなしで全件返却してしまう。

`get_page_tree()` は認証ユーザーの `user_id` を受け取らずサービスを呼び出しており、サービス側の `page_crud.get_tree(db)` にも visibility フィルタが存在しない。`list_pages()` はルーターで `_user_id` を取得しているが、サービス呼び出しに渡していない。

```python
# api_wiki.py:106-111 — user_id が渡されない
@router.get("/tree", response_model=List[WikiPageTreeNode])
def get_page_tree(
    db: Session = Depends(get_db),
    _user_id: int = Depends(get_current_user_id),  # ← 取得しているが使っていない
):
    return svc.get_page_tree(db)  # ← user_id 未渡し

# api_wiki.py:123-130
@router.get("/", response_model=List[WikiPageResponse])
def list_pages(
    tag_slug: Optional[str] = None,
    category_id: Optional[int] = None,
    db: Session = Depends(get_db),
    _user_id: int = Depends(get_current_user_id),  # ← 取得しているが使っていない
):
    return svc.list_pages(db, tag_slug=tag_slug, category_id=category_id)  # ← 未渡し
```

**影響範囲:** `private` ページの内容が全認証ユーザーに露出する。

**対策案:**
- `get_page_tree(db, user_id, is_admin)` のシグネチャに visibility フィルタを追加
- `list_pages(db, user_id, is_admin, ...)` にも同様に追加
- `page_crud.get_tree()` および `page_crud.get_all_pages()` に visibility フィルタクエリを実装

**推奨:** WIKI 実装フェーズ中に必ず修正。個別ページ取得 (`get_page_by_id`, `get_page_by_slug`) では `_check_visibility()` が正しく呼ばれているので、一覧系に同等の制御を追加するだけでよい。

---

### ISSUE-2-02: Wiki タスクリンクの書き込み権限チェックが欠落

**発見箇所:** `app/services/wiki_service.py:434-458`, `app/routers/api_wiki.py:222-229`
**優先度:** 高（セキュリティ）
**状態:** ✅ 解決済み（2026-02-25）

**内容:**
タスクリンク操作のサービス関数 3 件が `_check_write_permission()` を呼んでいないため、任意のユーザーが他人のページのタスクリンクを変更・削除できる。

```python
# wiki_service.py:434-443 — _check_write_permission() がない
def update_task_item_links(db, page_id, data, user_id):
    _require_page(db, page_id)  # ← ページ存在確認のみ
    task_link_crud.update_task_item_links(...)

# wiki_service.py:446-451
def add_task_link(db, page_id, task_id, user_id):
    _require_page(db, page_id)  # ← 同上

# wiki_service.py:454-458
def remove_task_link(db, page_id, task_id):
    _require_page(db, page_id)  # ← user_id すら受け取っていない
```

さらに `remove_task_link` のルーターは `_user_id` (アンダースコア付き) として受け取っており、サービスに渡すことができない。

**影響範囲:** タスクリンクの不正追加・削除。

**対策案:**
- 各サービス関数に `user_id: int, is_admin: bool` 引数を追加
- `_require_page()` 後に `_check_write_permission(page, user_id, is_admin)` を呼び出す
- ルーターの `_user_id` を `user_id` に変更してサービスに渡す

**解決内容:**
`wiki_service.py` の `update_task_item_links()`, `add_task_link()`, `remove_task_link()` の 3 関数に `user_id: int` および `is_admin: bool = False` 引数を追加し、`_require_page()` の直後に `_check_write_permission(page, user_id, is_admin)` を呼び出すよう修正。`api_wiki.py` の `remove_task_link` ルーターの `_user_id` を `user_id` に変更し、サービスに渡すよう修正（ISSUE-2-15 と合わせて対応）。

---

### ISSUE-2-03: Task サービスと DailyReport の密結合

**発見箇所:** `app/services/task_service.py:11-18`
**優先度:** 高（アーキテクチャ）
**状態:** 未解決（技術的負債）

**内容:**
`task_service.py` が `daily_report` CRUD・モデル・スキーマを直接インポートしている。Task と Report が別機能であるにもかかわらず、サービス層で直接依存関係が生まれており、将来的にモジュール分離・別アプリ化が困難になる。

```python
# task_service.py:11-18
from app.crud import daily_report as crud_report
from app.models.daily_report import DailyReport
from app.schemas.daily_report import DailyReportCreate
```

**影響範囲:** モジュール分離・テスト独立性。

**対策案:**
- コールバック/フック方式に変更: `task_service.done_task()` の完了イベントをコールバック引数で受け取る
- 将来的にはイベントバスパターン（Pub/Sub）で `task.done` イベントを発行し、`report_service` がサブスクライブする設計に移行する
- 短期対応: 少なくとも `done_task()` の引数に `on_done_callback: Optional[Callable]` を持たせることでテスト容易性を向上

---

### ISSUE-2-04: Log サービスと Alert サービスの密結合

**発見箇所:** `app/services/log_service.py:9`
**優先度:** 高（アーキテクチャ）
**状態:** 未解決（技術的負債）

**内容:**
`log_service.py` が `alert_service` を直接インポートしており、ログ収集とアラート生成が密結合している。ログ機能をアラートなしで独立テスト・再利用できない。

```python
# log_service.py:9
from app.services import alert_service
```

**影響範囲:** テスト独立性、モジュール再利用性。

**対策案:**
- ISSUE-2-03 と同様のコールバック/イベントバス方式への移行
- 短期対応: `create_log()` の呼び出し側 (router) でアラート評価を行い、サービス間依存を解消する

---

### ISSUE-2-05: Wiki ページ作成時に全文検索ベクタが更新されない

**発見箇所:** `app/services/wiki_service.py:287-306`
**優先度:** 中
**状態:** ✅ 解決済み（2026-02-25）

**内容:**
`update_page()` では `update_search_vector()` が呼ばれているが、`create_page()` では呼ばれていない。新規作成したページは全文検索の対象にならず、更新するまで検索ヒットしない。

```python
# wiki_service.py:287-306 — update_search_vector() の呼び出しがない
def create_page(db, data, user_id):
    ...
    page = page_crud.create_page(...)
    db.commit()
    db.refresh(page)
    return _to_detail_response(page, db)  # ← search_vector が空のまま

# update_page() には存在する（337-338行）
body_text = _extract_text_from_markdown(page.content or "")
page_crud.update_search_vector(db, page.id, f"{page.title} {body_text}")
```

**影響範囲:** 全文検索の検索精度（新規作成ページが検索不能）。

**対策案:**
`create_page()` の `db.commit()` 後に `page_crud.update_search_vector()` を追加。

**解決内容:**
`wiki_service.py` の `create_page()` 内で `page_crud.create_page()` 直後（`db.commit()` 前）に `_extract_text_from_markdown(content)` でテキスト抽出を行い、`page_crud.update_search_vector(db, page.id, f"{data.title} {body_text}")` を呼び出すよう修正。同一トランザクション内で search_vector が確実に設定される。

---

### ISSUE-2-06: Wiki ページツリー内の N+1 クエリ（lazy="select"）

**発見箇所:** `app/models/wiki_page.py:40-51`
**優先度:** 中（パフォーマンス）
**状態:** ✅ 解決済み（2026-02-25）

**内容:**
`WikiPage.linked_task_items` と `WikiPage.task_links` のロード方式が `lazy="select"` になっており、ページ一覧を取得する際に各ページごとに追加クエリが発生する。`tags` は `lazy="selectin"` で適切に設定されているが、タスクリンク系が漏れている。

```python
# wiki_page.py:40-51
linked_task_items = relationship(
    "TaskListItem",
    secondary=wiki_page_task_items,
    lazy="select",   # ← N+1 問題
)
task_links = relationship(
    "WikiPageTask",
    ...
    lazy="select",   # ← N+1 問題
)
```

**影響範囲:** ページ一覧・ツリー取得時のクエリ数。ページ数が多いと顕著に悪化。

**対策案:**
- 一覧用途では JOIN 取得または `lazy="selectin"` に変更
- ただし `task_links` はページ詳細でのみ必要なため `lazy="select"` のままにして、一覧クエリで明示的に `load_only()` / `noload()` を指定する方法も有効

**解決内容:**
`wiki_page.py` の `get_all_pages()` クエリに `joinedload(WikiPage.author)`, `joinedload(WikiPage.category)`, `noload(WikiPage.linked_task_items)`, `noload(WikiPage.task_links)`, `noload(WikiPage.attachments)` を追加。モデルの `lazy` 設定は変更せず、クエリレベルのオプションで N+1 を解消。一覧では不要な関係は `noload()` でロード抑制し、必要な `author`/`category` は `joinedload()` で JOIN 取得。

---

### ISSUE-2-07: SiteLink 一覧取得時の N+1 クエリ

**発見箇所:** `app/services/site_link_service.py:43-52`
**優先度:** 中（パフォーマンス）
**状態:** ✅ 解決済み（2026-02-25）

**内容:**
`_to_link_response()` が `_get_group_name()` を呼び出し、各サイトリンクごとに GROUP テーブルへのクエリを実行している。サイトリンク 100 件なら 101 クエリ（N+1）が発生する。

```python
# site_link_service.py:43-52
def _get_group_name(db: Session, group_id: int) -> str:
    group = crud.get_group(db, group_id)  # ← 各リンクごとにクエリ
    return group.name if group else ""

def _to_link_response(link: SiteLink, db: Session) -> SiteLinkResponse:
    group_name = _get_group_name(db, link.group_id) if link.group_id else None
```

**影響範囲:** サイトリンク一覧ページの応答速度。

**対策案:**
- `SiteLink` モデルに `group = relationship("SiteGroup", lazy="joined")` を追加して JOIN で取得する
- または `crud.get_links()` クエリ側で `joinedload(SiteLink.group)` を指定する

**解決内容:**
`app/models/site_link.py` の `SiteLink` モデルに `group = relationship("SiteGroup", foreign_keys=[group_id], lazy="joined")` を追加。`site_link_service.py` の `_get_group_name()` ヘルパーを削除し、`_to_link_response()` を `link.group.name if link.group else None` で group_name を取得するシンプルな実装に変更（`db` 引数も不要に）。全ての呼び出し元の `_to_link_response(link, db)` → `_to_link_response(link)` に更新。

---

### ISSUE-2-08: WikiPageVisibility 定数（Enum）が未定義

**発見箇所:** `app/models/wiki_page.py:21`, `app/schemas/wiki.py:71`
**優先度:** 中（保守性）
**状態:** ✅ 解決済み（2026-02-25）

**内容:**
`WikiPage.visibility` のカラム定義やスキーマで文字列リテラル `"internal"`, `"public"`, `"private"` が直書きされているが、`app/constants.py` に対応する Enum が存在しない。`TaskStatus`, `ItemStatus` 等の他定数と一貫性がない。

```python
# wiki_page.py:21 — 文字列ハードコーディング
visibility = Column(String(20), nullable=False, server_default="internal")

# schemas/wiki.py:71 — スキーマでも直書き
visibility: str = "internal"
```

**影響範囲:** 型安全性の欠如、タイポ時の実行時エラー、コード補完の効かない箇所が発生。

**対策案:**
`app/constants.py` に以下を追加:
```python
class WikiPageVisibility(str, Enum):
    PUBLIC = "public"
    INTERNAL = "internal"
    PRIVATE = "private"
```
モデル・スキーマ・サービスの文字列リテラルを置き換える。

**解決内容:**
`app/constants.py` に `WikiPageVisibility` クラスと `WikiPageVisibilityType` Literal 型を追加:
```python
class WikiPageVisibility:
    PUBLIC = "public"
    INTERNAL = "internal"
    PRIVATE = "private"

WikiPageVisibilityType = Literal["public", "internal", "private"]
```
他の定数（`TaskStatus`, `ItemStatus` 等）と同一の設計パターンで実装。

---

### ISSUE-2-09: Slug 生成の最大長チェック未実装

**発見箇所:** `app/services/wiki_service.py:41-57`
**優先度:** 中
**状態:** ✅ 解決済み（2026-02-25）

**内容:**
`generate_slug()` と `_make_unique_slug()` に最大長チェックがない。`wiki_pages.slug` カラムの上限は `String(500)` だが、非常に長いタイトルからは 500 文字超の slug が生成される可能性がある。さらに `_make_unique_slug()` の末尾にカウンター `"-{n}"` が付加されると上限超過リスクが高まる。

```python
# wiki_service.py:41-57
def generate_slug(title: str) -> str:
    ...
    return slug  # ← 長さチェックなし

def _make_unique_slug(db, base_slug, exclude_id=None):
    slug = base_slug
    counter = 2
    while page_crud.slug_exists(db, slug, exclude_id=exclude_id):
        slug = f"{base_slug}-{counter}"  # ← base_slug が 500 文字近いと上限超過
        counter += 1
    return slug
```

**影響範囲:** DB に slug を保存する際の `DataError`（500 文字超過）。

**対策案:**
`generate_slug()` 内または `_make_unique_slug()` の冒頭で `base_slug = base_slug[:480]` のように上限前切り捨てを行う（カウンター追加の余裕を確保）。

**解決内容:**
`wiki_service.py` に `_SLUG_MAX_BASE_LENGTH = 480` 定数を追加。`generate_slug()` の返り値を `return slug[:_SLUG_MAX_BASE_LENGTH]` で切り捨て、`_make_unique_slug()` の冒頭で `base_slug = base_slug[:_SLUG_MAX_BASE_LENGTH]` を適用。カウンターサフィックス `-NNN` を付加しても String(500) の DB カラム上限を超えない余裕を確保。

---

### ISSUE-2-10: カラーコードのバリデーションが未実装

**発見箇所:** `app/schemas/wiki.py:14`, `42`
**優先度:** 低〜中
**状態:** ✅ 解決済み（2026-02-25）

**内容:**
`WikiCategoryCreate.color` および `WikiTagCreate.color` は `str` 型で受け付けており、`#RRGGBB` 形式の正規表現バリデーションが存在しない。不正な文字列（例: `"red"`, `"<script>"`）が保存される可能性がある。

```python
# schemas/wiki.py:14
class WikiCategoryCreate(BaseModel):
    color: str = "#6c757d"  # ← regex バリデーションなし

# schemas/wiki.py:42
class WikiTagCreate(BaseModel):
    color: str = "#6c757d"  # ← 同上
```

**影響範囲:** フロントエンドでの CSS 注入リスク（低）、不正データ保存。

**対策案:**
Pydantic の `field_validator` または `Annotated[str, Field(pattern=r"^#[0-9A-Fa-f]{6}$")]` でバリデーションを追加。

**解決内容:**
`app/schemas/wiki.py` に `_ColorHex = Annotated[str, Field(pattern=r"^#[0-9A-Fa-f]{6}$")]` を定義し、`WikiCategoryCreate`, `WikiCategoryUpdate`, `WikiTagCreate` の `color` フィールドに適用。

---

### ISSUE-2-11: 秒数換算マジックナンバー `3600` の重複

**発見箇所:** `app/services/task_service.py:147-148,218-219`, `app/services/attendance_service.py:385-386,402-403`
**優先度:** 低
**状態:** ✅ 解決済み（2026-02-25）

**内容:**
1時間 = 3600 秒の変換ロジックが 4 箇所に重複している。単体テストやリファクタリングの際に変更漏れが生じやすい。

```python
# task_service.py:147-148
hours = task.total_seconds // 3600
mins = (task.total_seconds % 3600) // 60

# attendance_service.py:385-386
h = work_seconds // 3600
m = (work_seconds % 3600) // 60
```

**対策案:**
`app/core/utils.py` に `seconds_to_hms(seconds: int) -> tuple[int, int, int]` ユーティリティを追加し、全箇所から呼び出す。

**解決内容:**
`app/core/utils.py` に `seconds_to_hm(seconds: int) -> Tuple[int, int]` を追加。`task_service.py`（2 箇所）と `attendance_service.py`（2 箇所）で `3600` パターンを `seconds_to_hm()` 呼び出しに置き換え。

---

### ISSUE-2-12: ヘルスチェック成功判定の HTTP ステータス範囲がハードコーディング

**発見箇所:** `app/services/site_link_service.py:216`
**優先度:** 低
**状態:** ✅ 解決済み（2026-02-25）

**内容:**
HTTP 200〜399 を「成功」と判定するロジックが定数化されておらず、変更・テストが困難。また `399` の上限も RFC 的に一般的ではない（`3xx` はリダイレクトであり通常は `200〜299` を成功とすることが多い）。

```python
# site_link_service.py:216
if 200 <= code <= 399:
    status = "up"
```

**対策案:**
`app/constants.py` または `site_link_service.py` 冒頭に `SITE_CHECK_SUCCESS_RANGE = range(200, 400)` 等の定数を定義。上限値も要件確認の上で適切な値に設定する。

**解決内容:**
`app/services/site_link_service.py` 冒頭に `_HTTP_SUCCESS_MIN = 200` / `_HTTP_SUCCESS_MAX = 399` を定義し、判定式を `if _HTTP_SUCCESS_MIN <= code <= _HTTP_SUCCESS_MAX:` に置き換え。

---

### ISSUE-2-13: エラーメッセージ切り捨て長さのマジックナンバー

**発見箇所:** `app/services/site_link_service.py:240`
**優先度:** 低
**状態:** ✅ 解決済み（2026-02-25）

**内容:**
例外メッセージを `[:200]` で切り捨てているが、この `200` の意味が不明瞭。DB カラムの上限値（`last_error TEXT`）には無制限なのに中途半端な切り捨てとなっている。

```python
# site_link_service.py:240
err = str(exc)[:200]
```

**対策案:**
定数 `SITE_ERROR_MAX_LENGTH = 500` を定義して使用するか、DB カラム容量が問題でなければ切り捨て自体を削除する。

**解決内容:**
`site_link_service.py` の冒頭に `_SITE_ERROR_MAX_LENGTH = 200` を定数として定義し、`str(exc)[:200]` を `str(exc)[:_SITE_ERROR_MAX_LENGTH]` に置き換え。同ファイルに既存の `_HTTP_SUCCESS_MIN`/`_HTTP_SUCCESS_MAX` 定数と同じスタイルで追加。

---

### ISSUE-2-14: ページルート登録の拡張性欠如

**発見箇所:** `app/routers/pages.py`
**優先度:** 低（設計）
**状態:** 未解決

**内容:**
HTML ページルート (`/tasks`, `/wiki`, `/sites` 等) が `pages.py` にべた書きされており、機能追加のたびにこのファイルを編集する必要がある。`main.py` の `register_page()` との役割が重複している部分もある。

**影響範囲:** 機能追加時の変更箇所が増加。

**対策案:**
中長期的に `portal.register_page(path, template, nav_label)` の方式を整備し、`pages.py` の内容を `main.py` 側の登録に統合する。ページルート登録を一箇所に集約することで見通しが良くなる。

---

### ISSUE-2-15: Wiki タスクリンクの「削除権限チェック漏れ」と `remove_task_link` の user_id 未渡し

**発見箇所:** `app/routers/api_wiki.py:222-229`, `app/services/wiki_service.py:454-458`
**優先度:** 高（セキュリティ）
**状態:** ✅ 解決済み（2026-02-25）

**内容:**
`DELETE /{page_id}/tasks/{task_id}` ルーターが `_user_id` (アンダースコア) として user_id を受け取っており、`svc.remove_task_link(db, page_id, task_id)` にユーザー情報を渡していない（ISSUE-2-02 の一部）。

```python
# api_wiki.py:222-229
@router.delete("/{page_id}/tasks/{task_id}", status_code=204)
def remove_task_link(
    page_id: int,
    task_id: int,
    db: Session = Depends(get_db),
    _user_id: int = Depends(get_current_user_id),  # ← アンダースコア付き＝未使用
):
    svc.remove_task_link(db, page_id, task_id)  # ← user_id なし
```

**影響範囲:** 誰でも任意ページからタスクリンクを削除できる。

**対策案:** ISSUE-2-02 と合わせて修正。

**解決内容:** ISSUE-2-02 と同時対応。`api_wiki.py` の `remove_task_link` ルーターで `_user_id` を `user_id` に変更し、`svc.remove_task_link(db, page_id, task_id, user_id)` として渡すよう修正。

---

## 対応優先度まとめ

| ID | タイトル | 優先度 | カテゴリ | 状態 |
|----|---------|--------|---------|------|
| ~~ISSUE-2-01~~ | ~~Wiki ツリー/一覧の visibility フィルタ欠落~~ | ~~**高**~~ | ~~セキュリティ~~ | ✅ |
| ~~ISSUE-2-02~~ | ~~Wiki タスクリンク書き込み権限チェック欠落~~ | ~~**高**~~ | ~~セキュリティ~~ | ✅ |
| ~~ISSUE-2-15~~ | ~~remove_task_link の user_id 未渡し~~ | ~~**高**~~ | ~~セキュリティ~~ | ✅ |
| ISSUE-2-03 | Task → DailyReport の密結合 | **高** | アーキテクチャ | 技術的負債 |
| ISSUE-2-04 | Log → Alert の密結合 | **高** | アーキテクチャ | 技術的負債 |
| ~~ISSUE-2-05~~ | ~~ページ作成時に search_vector 未更新~~ | ~~中~~ | ~~バグ~~ | ✅ |
| ~~ISSUE-2-06~~ | ~~WikiPage の N+1 クエリ (lazy="select")~~ | ~~中~~ | ~~パフォーマンス~~ | ✅ |
| ~~ISSUE-2-07~~ | ~~SiteLink 一覧の N+1 クエリ~~ | ~~中~~ | ~~パフォーマンス~~ | ✅ |
| ~~ISSUE-2-08~~ | ~~WikiPageVisibility Enum 未定義~~ | ~~中~~ | ~~保守性~~ | ✅ |
| ~~ISSUE-2-09~~ | ~~Slug 最大長チェック未実装~~ | ~~中~~ | ~~バグリスク~~ | ✅ |
| ~~ISSUE-2-10~~ | ~~カラーコードのバリデーション欠落~~ | ~~低〜中~~ | ~~セキュリティ~~ | ✅ |
| ~~ISSUE-2-11~~ | ~~マジックナンバー `3600` の重複~~ | ~~低~~ | ~~保守性~~ | ✅ |
| ~~ISSUE-2-12~~ | ~~ヘルスチェック成功判定範囲のハードコーディング~~ | ~~低~~ | ~~保守性~~ | ✅ |
| ~~ISSUE-2-13~~ | ~~エラーメッセージ切り捨て長さのマジックナンバー~~ | ~~低~~ | ~~保守性~~ | ✅ |
| ISSUE-2-14 | ページルート登録の拡張性欠如 | 低 | 設計 | 技術的負債 |
