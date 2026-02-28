# ISSUE-5: 未解決の技術的負債（issue1〜issue4の未完了項目まとめ）

> 作成日: 2026-02-25
> 参照元: issue2.md（ISSUE-2-03, 2-04, 2-14）
>
> **注記**: `docs/issue1.md` は存在しない（`docs/issue_report.md` は ISSUE-6 修正報告書であり未完了項目なし）。
> `docs/issue3.md` は全20件解決済み。`docs/issue4.md` は ISSUE-4-05「対応不要」を除き全件解決済みのため本書に記載しない。

---

## 未解決一覧

| ID | 概要 | 優先度 | 種別 |
|----|------|--------|------|
| [ISSUE-5-01](#issue-5-01) | Task → DailyReport 密結合 | 高 | 技術的負債 |
| [ISSUE-5-02](#issue-5-02) | Log → Alert 密結合 | 高 | 技術的負債 |
| [ISSUE-5-03](#issue-5-03) | ページルート登録の拡張性欠如 | 低 | 技術的負債 |

---

## ISSUE-5-01

**元ID**: ISSUE-2-03
**概要**: Task → DailyReport の密結合（技術的負債）
**優先度**: 高
**ステータス**: 未解決

### 問題

`app/services/task_service.py` の `done_task()` が `daily_report` 関連の CRUD・モデル・スキーマを直接インポートしている。

```python
# task_service.py 内
from app.crud.daily_report import crud_daily_report
from app.models.daily_report import DailyReport
from app.schemas.daily_report import DailyReportCreate
```

これにより、Task と DailyReport を別アプリ・別モジュールに分離することができない。

### 影響範囲

- `app/services/task_service.py`: `done_task()`, `batch_done()`
- `app/crud/daily_report.py`: `create_report()`
- `app/models/daily_report.py`
- `app/schemas/daily_report.py` (`DailyReportCreate`)

### 対策案

**コールバック / フック方式**（推奨）

```python
# task_service.py
_on_task_done_hooks: list[Callable] = []

def register_on_task_done(hook: Callable[[db, task], None]):
    _on_task_done_hooks.append(hook)

def done_task(db, user_id, task_id):
    task = _get_owned_task(db, user_id, task_id)
    for hook in _on_task_done_hooks:
        hook(db, task)
    db.delete(task)
    db.commit()
```

```python
# main.py（アプリ起動時）
from app.services.task_service import register_on_task_done
from app.services.daily_report_service import create_report_from_task

register_on_task_done(create_report_from_task)
```

**イベントバス方式**（将来）: アプリ内ドメインイベント（`TaskDoneEvent`）を発行し、DailyReport サービスがサブスクライブする。

### 現状の暫定措置

同一アプリ内に同居を強制（分離コストが便益を上回るため現時点は許容）。

---

## ISSUE-5-02

**元ID**: ISSUE-2-04
**概要**: Log → Alert 密結合（技術的負債）
**優先度**: 高
**ステータス**: 未解決

### 問題

`app/services/log_source_service.py`（または `app/routers/api_logs.py`）が Alert の CRUD・モデルを直接インポートしてアラートを生成している。

```python
# log_source_service.py 内
from app.crud.alert import crud_alert
from app.models.alert import Alert
```

Log 収集とアラート生成が密結合しているため、Log サービスを独立させることができない。

### 影響範囲

- `app/services/log_source_service.py`: `scan_source()` のアラート生成部分
- `app/crud/alert.py`: `create_alert()`
- `app/models/alert.py`

### 対策案

**コールバック方式**（推奨、ISSUE-5-01 と同パターン）

```python
# log_source_service.py
_on_change_detected_hooks: list[Callable] = []

def register_on_change_detected(hook: Callable[[db, source, changed_paths], None]):
    _on_change_detected_hooks.append(hook)

def scan_source(db, source_id):
    ...
    if changed_paths and source.alert_on_change:
        for hook in _on_change_detected_hooks:
            hook(db, source, changed_paths)
```

```python
# main.py
from app.services.log_source_service import register_on_change_detected
from app.services.alert_service import create_change_alert

register_on_change_detected(create_change_alert)
```

**イベントバス方式**（将来）: `LogChangeEvent` をドメインイベントとして発行。

### 現状の暫定措置

同一アプリ内に同居を強制（分離コストが便益を上回るため現時点は許容）。

---

## ISSUE-5-03

**元ID**: ISSUE-2-14
**概要**: ページルート登録の拡張性欠如（技術的負債）
**優先度**: 低
**ステータス**: 未解決

### 問題

`app/routers/pages.py` にページルートが全て集中しており、新しいページを追加するたびに同ファイルを編集する必要がある。`portal.register_page()` API が存在するが、機能別ルーターがそれぞれ自分のページルートを登録できる仕組みがない。

```python
# 現状: pages.py にすべての GET ページルートが集中
@router.get("/tasks")
async def tasks_page(request: Request): ...

@router.get("/sites")
async def sites_page(request: Request): ...

# wiki など新機能追加のたびに pages.py を編集
@router.get("/wiki")
async def wiki_index_page(request: Request): ...
```

### 影響範囲

- `app/routers/pages.py`: 全ページルートを一括管理
- 新機能追加時の変更箇所が pages.py + api_xxx.py の2ファイルに分散

### 対策案

**機能別ページルーター方式**（推奨）

各機能モジュールが自分のページルートを定義し、`main.py` で一括登録する。

```python
# app/routers/wiki_pages.py（新規）
from fastapi import APIRouter, Request
from portal_core.app_factory import render_page

router = APIRouter()

@router.get("/wiki")
async def wiki_index(request: Request):
    return render_page(request, "wiki_list.html")

@router.get("/wiki/{slug}")
async def wiki_page(request: Request, slug: str):
    return render_page(request, "wiki_page.html", {"slug": slug})
```

```python
# main.py
from app.routers import wiki_pages
portal.register_router(wiki_pages.router)
```

**`portal.register_page()` 拡張方式**: `register_page(path, template, path_params=None)` でパスパラメータ付きルートを登録できるよう API を拡張する。

### 現状の暫定措置

`pages.py` を編集し続ける（変更コストが低いため許容）。新機能はできるだけ機能別ルーターに近接させて定義することを推奨。

---

## 対応方針サマリー

| ID | 対応方針 | 対応時期の目安 |
|----|----------|--------------|
| ISSUE-5-01 | コールバック方式でフック登録に変更 | 次フェーズのアーキテクチャ改善時 |
| ISSUE-5-02 | コールバック方式でフック登録に変更 | 次フェーズのアーキテクチャ改善時 |
| ISSUE-5-03 | 機能別ページルーター方式に移行 | 新機能追加時に順次対応 |

ISSUE-5-01 と ISSUE-5-02 は同一パターンの問題であるため、コールバック/フック方式の基盤を共通化して一括対応することが効率的。
