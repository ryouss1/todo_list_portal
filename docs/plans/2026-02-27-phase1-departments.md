# Phase 1: groups → departments 置き換え 実装計画

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** `groups` テーブル（平坦構造）を `departments`（parent_id による階層ツリー）に完全置き換えし、`users.group_id` → `users.department_id`、`log_sources.group_id` → `log_sources.department_id` にリネームする。

**Architecture:** portal_core に `Department` モデル・CRUD・Schema・Service・Router を新規作成。Alembic でデータ移行マイグレーションを実施。`Group` モデルを削除し、app 側の shim・サービス・テンプレート・JS を全て更新する。

**Tech Stack:** FastAPI, SQLAlchemy 2.0, Alembic, pytest, portal_core パッケージ構成（`pip install -e portal_core/`）

---

## 変更ファイル一覧

| ファイル | 変更内容 |
|---------|---------|
| `portal_core/portal_core/models/department.py` | 新規作成（Department モデル） |
| `portal_core/portal_core/models/group.py` | 削除 |
| `portal_core/portal_core/models/__init__.py` | Group → Department に更新 |
| `portal_core/portal_core/models/user.py` | group_id → department_id リネーム |
| `portal_core/portal_core/crud/department.py` | 新規作成（Department CRUD） |
| `portal_core/portal_core/crud/group.py` | 削除 |
| `portal_core/portal_core/crud/__init__.py` | Group → Department に更新 |
| `portal_core/portal_core/schemas/department.py` | 新規作成（Department スキーマ） |
| `portal_core/portal_core/schemas/group.py` | 削除 |
| `portal_core/portal_core/schemas/__init__.py` | Group → Department に更新 |
| `portal_core/portal_core/schemas/user.py` | group_id/group_name → department_id/department_name |
| `portal_core/portal_core/services/department_service.py` | 新規作成（group_service を改名・拡張） |
| `portal_core/portal_core/services/group_service.py` | 削除 |
| `portal_core/portal_core/services/user_service.py` | group_map → department_map |
| `portal_core/portal_core/services/__init__.py` | Group → Department に更新 |
| `portal_core/portal_core/routers/api_departments.py` | 新規作成（/api/departments/、tree エンドポイント追加） |
| `portal_core/portal_core/routers/api_groups.py` | 削除 |
| `portal_core/portal_core/routers/__init__.py` | 更新 |
| `portal_core/portal_core/app_factory.py` | groups → departments ルーター登録更新 |
| `portal_core/tests/test_groups.py` | 削除 |
| `portal_core/tests/test_departments.py` | 新規作成 |
| `app/models/group.py` | Department を再エクスポートする shim に更新 |
| `app/models/__init__.py` | Department インポート追加 |
| `app/crud/group.py` | department CRUD を再エクスポート shim に更新 |
| `app/services/group_service.py` | department_service を再エクスポート shim に更新 |
| `app/routers/api_groups.py` | 削除（portal_core がルート登録） |
| `app/models/log_source.py` | group_id → department_id, FK → departments |
| `app/schemas/log_source.py` | group_id → department_id |
| `app/crud/user.py` | get_users_in_group → get_users_in_department |
| `app/services/summary_service.py` | group_id → department_id |
| `app/services/wiki_service.py` | _get_user_group_id → _get_user_department_id |
| `app/crud/wiki_page.py` | raw SQL group_id → department_id |
| `templates/summary.html` | group-filter → department-filter |
| `templates/calendar.html` | group-filter → department-filter |
| `templates/logs.html` | source-group-id → source-department-id |
| `portal_core/portal_core/static/js/users.js` (またはapp側) | /api/groups/ → /api/departments/ |
| `static/js/calendar.js` | group_id → department_id |
| `static/js/summary.js` (存在する場合) | group_id → department_id |
| `alembic/versions/XXXX_groups_to_departments.py` | データ移行マイグレーション |
| `tests/test_log_sources.py` | group_id → department_id 更新 |

---

## Task 1: Department モデル作成

**Files:**
- Create: `portal_core/portal_core/models/department.py`
- Modify: `portal_core/portal_core/models/__init__.py`

**Step 1: 失敗するテストを書く**

```python
# portal_core/tests/test_departments.py（新規作成）
from portal_core.models.department import Department


def test_department_model_columns():
    cols = {c.name for c in Department.__table__.columns}
    assert "id" in cols
    assert "name" in cols
    assert "code" in cols
    assert "parent_id" in cols
    assert "sort_order" in cols
    assert "is_active" in cols
    assert "created_at" in cols
    assert "updated_at" in cols


def test_department_tablename():
    assert Department.__tablename__ == "departments"
```

**Step 2: テスト失敗確認**
```bash
cd portal_core && pytest tests/test_departments.py -v
```
Expected: FAIL with ImportError

**Step 3: Department モデル実装**

```python
# portal_core/portal_core/models/department.py
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.sql import func

from portal_core.database import Base


class Department(Base):
    __tablename__ = "departments"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False, unique=True)
    code = Column(String(50), nullable=True, unique=True)
    description = Column(String(500), nullable=True)
    parent_id = Column(
        Integer,
        ForeignKey("departments.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    sort_order = Column(Integer, nullable=False, default=0)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
```

**Step 4: `portal_core/portal_core/models/__init__.py` 更新**

```python
# 追加
from portal_core.models.department import Department

# 削除（後で行う — 今は両方残す）
# from portal_core.models.group import Group
```

**Step 5: テスト合格確認**
```bash
cd portal_core && pytest tests/test_departments.py -v
```
Expected: PASS

**Step 6: コミット**
```bash
git add portal_core/portal_core/models/department.py portal_core/portal_core/models/__init__.py portal_core/tests/test_departments.py
git commit -m "feat: add Department model with hierarchical tree structure"
```

---

## Task 2: Department CRUD

**Files:**
- Create: `portal_core/portal_core/crud/department.py`
- Modify: `portal_core/portal_core/crud/__init__.py`
- Modify: `portal_core/tests/test_departments.py`（テスト追加）

**Step 1: 失敗するテストを追加**

```python
# portal_core/tests/test_departments.py に追加
from portal_core.crud.department import (
    get_department,
    get_departments,
    create_department,
    update_department,
    delete_department,
    count_members,
)


def test_get_departments_empty(db_session):
    result = get_departments(db_session)
    assert isinstance(result, list)


def test_create_department(db_session):
    dept = create_department(db_session, name="Engineering", sort_order=0)
    assert dept.id is not None
    assert dept.name == "Engineering"
    assert dept.is_active is True
    assert dept.parent_id is None


def test_create_department_with_parent(db_session):
    parent = create_department(db_session, name="Technology", sort_order=0)
    child = create_department(db_session, name="Backend", parent_id=parent.id, sort_order=0)
    assert child.parent_id == parent.id


def test_count_members(db_session, test_user):
    dept = create_department(db_session, name="HR", sort_order=0)
    from portal_core.models.user import User
    test_user.department_id = dept.id
    db_session.flush()
    assert count_members(db_session, dept.id) == 1
```

**Step 2: テスト失敗確認**
```bash
cd portal_core && pytest tests/test_departments.py -k "test_get_departments or test_create_department or test_count_members" -v
```
Expected: FAIL (ImportError)

**Step 3: Department CRUD 実装**

```python
# portal_core/portal_core/crud/department.py
from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from portal_core.crud.base import CRUDBase
from portal_core.models.department import Department
from portal_core.models.user import User

_crud = CRUDBase(Department)

get_department = _crud.get
delete_department = _crud.delete


def get_departments(db: Session) -> list:
    return (
        db.query(Department)
        .order_by(Department.sort_order, Department.name)
        .all()
    )


def get_departments_tree(db: Session) -> list:
    """全部門をソート順で返す（フロントエンド側でツリー構築）"""
    return (
        db.query(Department)
        .filter(Department.is_active.is_(True))
        .order_by(Department.sort_order, Department.name)
        .all()
    )


def create_department(
    db: Session,
    name: str,
    code: Optional[str] = None,
    description: Optional[str] = None,
    parent_id: Optional[int] = None,
    sort_order: int = 0,
    is_active: bool = True,
) -> Department:
    dept = Department(
        name=name,
        code=code,
        description=description,
        parent_id=parent_id,
        sort_order=sort_order,
        is_active=is_active,
    )
    db.add(dept)
    db.flush()
    return dept


def update_department(db: Session, dept: Department, data: dict) -> Department:
    for key, value in data.items():
        if value is not None:
            setattr(dept, key, value)
    db.flush()
    return dept


def count_members(db: Session, department_id: int) -> int:
    return (
        db.query(func.count(User.id))
        .filter(User.department_id == department_id)
        .scalar()
        or 0
    )
```

**Step 4: `portal_core/portal_core/crud/__init__.py` 更新**

```python
from portal_core.crud.department import (
    get_department,
    get_departments,
    get_departments_tree,
    create_department,
    update_department,
    delete_department,
    count_members as count_department_members,
)
```

**Step 5: テスト合格確認**

> 注意: `test_count_members` は Task 6（User モデルの department_id 追加）後にパスする。今は他のテストのみ確認。

```bash
cd portal_core && pytest tests/test_departments.py -k "test_get_departments_empty or test_create_department_with_parent" -v
```

**Step 6: コミット**
```bash
git add portal_core/portal_core/crud/department.py portal_core/portal_core/crud/__init__.py
git commit -m "feat: add Department CRUD functions"
```

---

## Task 3: Department スキーマ

**Files:**
- Create: `portal_core/portal_core/schemas/department.py`
- Modify: `portal_core/portal_core/schemas/__init__.py`

**Step 1: 失敗するテストを追加**

```python
# portal_core/tests/test_departments.py に追加
def test_department_response_schema():
    from portal_core.schemas.department import DepartmentResponse
    from datetime import datetime
    resp = DepartmentResponse(
        id=1,
        name="Engineering",
        code=None,
        description=None,
        parent_id=None,
        sort_order=0,
        is_active=True,
        member_count=0,
        created_at=datetime.now(),
        updated_at=None,
    )
    assert resp.name == "Engineering"
    assert resp.member_count == 0
```

**Step 2: テスト失敗確認**
```bash
cd portal_core && pytest tests/test_departments.py::test_department_response_schema -v
```

**Step 3: スキーマ実装**

```python
# portal_core/portal_core/schemas/department.py
from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class DepartmentCreate(BaseModel):
    name: str
    code: Optional[str] = None
    description: Optional[str] = None
    parent_id: Optional[int] = None
    sort_order: int = 0
    is_active: bool = True


class DepartmentUpdate(BaseModel):
    name: Optional[str] = None
    code: Optional[str] = None
    description: Optional[str] = None
    parent_id: Optional[int] = None
    sort_order: Optional[int] = None
    is_active: Optional[bool] = None


class DepartmentResponse(BaseModel):
    id: int
    name: str
    code: Optional[str] = None
    description: Optional[str] = None
    parent_id: Optional[int] = None
    sort_order: int
    is_active: bool
    member_count: int = 0
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
```

**Step 4: `__init__.py` 更新**

```python
from portal_core.schemas.department import (
    DepartmentCreate,
    DepartmentUpdate,
    DepartmentResponse,
)
```

**Step 5: テスト合格確認**
```bash
cd portal_core && pytest tests/test_departments.py::test_department_response_schema -v
```

**Step 6: コミット**
```bash
git add portal_core/portal_core/schemas/department.py portal_core/portal_core/schemas/__init__.py
git commit -m "feat: add Department Pydantic schemas"
```

---

## Task 4: Department Service

**Files:**
- Create: `portal_core/portal_core/services/department_service.py`
- Modify: `portal_core/portal_core/services/__init__.py`

**Step 1: 失敗するテストを追加**

```python
# portal_core/tests/test_departments.py に追加
def test_department_service_create(db_session):
    from portal_core.services.department_service import (
        create_department_svc,
        get_departments_svc,
    )
    from portal_core.schemas.department import DepartmentCreate

    data = DepartmentCreate(name="Sales")
    dept = create_department_svc(db_session, data)
    assert dept.id is not None

    all_depts = get_departments_svc(db_session)
    assert any(d.name == "Sales" for d in all_depts)


def test_department_service_conflict(db_session):
    from portal_core.services.department_service import create_department_svc
    from portal_core.schemas.department import DepartmentCreate
    from portal_core.core.exceptions import ConflictError

    data = DepartmentCreate(name="UniqueTest")
    create_department_svc(db_session, data)
    import pytest
    with pytest.raises(ConflictError):
        create_department_svc(db_session, DepartmentCreate(name="UniqueTest"))
```

**Step 2: テスト失敗確認**
```bash
cd portal_core && pytest tests/test_departments.py -k "test_department_service" -v
```

**Step 3: Department Service 実装**

```python
# portal_core/portal_core/services/department_service.py
from typing import List

from sqlalchemy.orm import Session

from portal_core.core.exceptions import ConflictError, NotFoundError
from portal_core.crud import department as crud_dept
from portal_core.models.department import Department
from portal_core.schemas.department import (
    DepartmentCreate,
    DepartmentResponse,
    DepartmentUpdate,
)


def _to_response(db: Session, dept: Department) -> DepartmentResponse:
    member_count = crud_dept.count_department_members(db, dept.id)
    return DepartmentResponse(
        id=dept.id,
        name=dept.name,
        code=dept.code,
        description=dept.description,
        parent_id=dept.parent_id,
        sort_order=dept.sort_order,
        is_active=dept.is_active,
        member_count=member_count,
        created_at=dept.created_at,
        updated_at=dept.updated_at,
    )


def get_departments_svc(db: Session) -> List[Department]:
    return crud_dept.get_departments(db)


def get_department_svc(db: Session, dept_id: int) -> Department:
    dept = crud_dept.get_department(db, dept_id)
    if not dept:
        raise NotFoundError("Department not found")
    return dept


def create_department_svc(db: Session, data: DepartmentCreate) -> Department:
    existing = db.query(Department).filter(Department.name == data.name).first()
    if existing:
        raise ConflictError("Department name already exists")
    return crud_dept.create_department(
        db,
        name=data.name,
        code=data.code,
        description=data.description,
        parent_id=data.parent_id,
        sort_order=data.sort_order,
        is_active=data.is_active,
    )


def update_department_svc(
    db: Session, dept_id: int, data: DepartmentUpdate
) -> Department:
    dept = get_department_svc(db, dept_id)
    update_data = data.model_dump(exclude_unset=True)
    if "name" in update_data:
        existing = (
            db.query(Department)
            .filter(Department.name == update_data["name"], Department.id != dept_id)
            .first()
        )
        if existing:
            raise ConflictError("Department name already exists")
    return crud_dept.update_department(db, dept, update_data)


def delete_department_svc(db: Session, dept_id: int) -> None:
    dept = get_department_svc(db, dept_id)
    crud_dept.delete_department(db, dept)
```

**Step 4: `__init__.py` 更新**

```python
from portal_core.services.department_service import (
    get_departments_svc,
    get_department_svc,
    create_department_svc,
    update_department_svc,
    delete_department_svc,
)
```

**Step 5: テスト合格確認**
```bash
cd portal_core && pytest tests/test_departments.py -k "test_department_service" -v
```

**Step 6: コミット**
```bash
git add portal_core/portal_core/services/department_service.py portal_core/portal_core/services/__init__.py
git commit -m "feat: add Department service with ConflictError handling"
```

---

## Task 5: Department Router + app_factory 更新

**Files:**
- Create: `portal_core/portal_core/routers/api_departments.py`
- Modify: `portal_core/portal_core/routers/__init__.py`
- Modify: `portal_core/portal_core/app_factory.py`
- Modify: `portal_core/tests/test_departments.py`（API テスト追加）

**Step 1: 失敗するテストを追加**

```python
# portal_core/tests/test_departments.py に追加（client フィクスチャ使用）
def test_get_departments_api(client):
    resp = client.get("/api/departments/")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_create_department_api_admin(client):
    resp = client.post("/api/departments/", json={"name": "Engineering", "sort_order": 0})
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Engineering"
    assert "id" in data


def test_create_department_api_requires_admin(client_user2):
    resp = client_user2.post("/api/departments/", json={"name": "Test"})
    assert resp.status_code == 403


def test_update_department_api(client):
    create_resp = client.post("/api/departments/", json={"name": "OldName"})
    dept_id = create_resp.json()["id"]
    resp = client.put(f"/api/departments/{dept_id}", json={"name": "NewName"})
    assert resp.status_code == 200
    assert resp.json()["name"] == "NewName"


def test_delete_department_api(client):
    create_resp = client.post("/api/departments/", json={"name": "ToDelete"})
    dept_id = create_resp.json()["id"]
    resp = client.delete(f"/api/departments/{dept_id}")
    assert resp.status_code == 204


def test_get_departments_tree_api(client):
    resp = client.get("/api/departments/tree")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)
```

**Step 2: テスト失敗確認**
```bash
cd portal_core && pytest tests/test_departments.py -k "test_get_departments_api or test_create_department_api" -v
```
Expected: FAIL (404 or Connection Error)

**Step 3: Router 実装**

```python
# portal_core/portal_core/routers/api_departments.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from portal_core.core.deps import get_current_user_id, require_admin
from portal_core.core.exceptions import ConflictError, NotFoundError
from portal_core.database import get_db
from portal_core.schemas.department import (
    DepartmentCreate,
    DepartmentResponse,
    DepartmentUpdate,
)
from portal_core.services.department_service import (
    create_department_svc,
    delete_department_svc,
    get_department_svc,
    get_departments_svc,
    update_department_svc,
)

router = APIRouter(prefix="/api/departments", tags=["departments"])


@router.get("/", response_model=list[DepartmentResponse])
def list_departments(
    db: Session = Depends(get_db),
    _user_id: int = Depends(get_current_user_id),
):
    depts = get_departments_svc(db)
    return [
        DepartmentResponse(
            id=d.id,
            name=d.name,
            code=d.code,
            description=d.description,
            parent_id=d.parent_id,
            sort_order=d.sort_order,
            is_active=d.is_active,
            member_count=0,
            created_at=d.created_at,
            updated_at=d.updated_at,
        )
        for d in depts
    ]


@router.get("/tree", response_model=list[DepartmentResponse])
def get_departments_tree(
    db: Session = Depends(get_db),
    _user_id: int = Depends(get_current_user_id),
):
    """active な部門のみ返す（フロントエンド側でツリー構築）"""
    from portal_core.crud.department import get_departments_tree as _tree
    depts = _tree(db)
    return [
        DepartmentResponse(
            id=d.id,
            name=d.name,
            code=d.code,
            description=d.description,
            parent_id=d.parent_id,
            sort_order=d.sort_order,
            is_active=d.is_active,
            member_count=0,
            created_at=d.created_at,
            updated_at=d.updated_at,
        )
        for d in depts
    ]


@router.post("/", response_model=DepartmentResponse, status_code=201)
def create_department(
    data: DepartmentCreate,
    db: Session = Depends(get_db),
    _user_id: int = Depends(require_admin),
):
    try:
        dept = create_department_svc(db, data)
        db.commit()
        db.refresh(dept)
    except ConflictError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return DepartmentResponse(
        id=dept.id,
        name=dept.name,
        code=dept.code,
        description=dept.description,
        parent_id=dept.parent_id,
        sort_order=dept.sort_order,
        is_active=dept.is_active,
        member_count=0,
        created_at=dept.created_at,
        updated_at=dept.updated_at,
    )


@router.put("/{dept_id}", response_model=DepartmentResponse)
def update_department(
    dept_id: int,
    data: DepartmentUpdate,
    db: Session = Depends(get_db),
    _user_id: int = Depends(require_admin),
):
    try:
        dept = update_department_svc(db, dept_id, data)
        db.commit()
        db.refresh(dept)
    except NotFoundError:
        raise HTTPException(status_code=404, detail="Department not found")
    except ConflictError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return DepartmentResponse(
        id=dept.id,
        name=dept.name,
        code=dept.code,
        description=dept.description,
        parent_id=dept.parent_id,
        sort_order=dept.sort_order,
        is_active=dept.is_active,
        member_count=0,
        created_at=dept.created_at,
        updated_at=dept.updated_at,
    )


@router.delete("/{dept_id}", status_code=204)
def delete_department(
    dept_id: int,
    db: Session = Depends(get_db),
    _user_id: int = Depends(require_admin),
):
    try:
        delete_department_svc(db, dept_id)
        db.commit()
    except NotFoundError:
        raise HTTPException(status_code=404, detail="Department not found")
```

**Step 4: `portal_core/portal_core/routers/__init__.py` 更新**

```python
from portal_core.routers.api_departments import router as departments_router
```
（既存の `api_groups` のエントリを削除または `api_departments` に置換）

**Step 5: `portal_core/portal_core/app_factory.py` 更新**

`setup_core()` 内のルーター登録を更新:
```python
# 変更前
from portal_core.routers.api_groups import router as groups_router
self.app.include_router(groups_router)

# 変更後
from portal_core.routers.api_departments import router as departments_router
self.app.include_router(departments_router)
```

**Step 6: テスト合格確認**
```bash
cd portal_core && pytest tests/test_departments.py -k "test_get_departments_api or test_create_department_api or test_update_department or test_delete_department or test_get_departments_tree" -v
```

**Step 7: コミット**
```bash
git add portal_core/portal_core/routers/api_departments.py portal_core/portal_core/routers/__init__.py portal_core/portal_core/app_factory.py
git commit -m "feat: add Department API router (/api/departments/), replace /api/groups/"
```

---

## Task 6: User モデル更新 (portal_core) + Group コード削除

**Files:**
- Modify: `portal_core/portal_core/models/user.py`
- Modify: `portal_core/portal_core/schemas/user.py`
- Modify: `portal_core/portal_core/services/user_service.py`
- Delete: `portal_core/portal_core/models/group.py`
- Delete: `portal_core/portal_core/crud/group.py`
- Delete: `portal_core/portal_core/schemas/group.py`
- Delete: `portal_core/portal_core/services/group_service.py`
- Delete: `portal_core/portal_core/routers/api_groups.py`
- Modify: `portal_core/portal_core/models/__init__.py`（Group import 削除）

**Step 1: 失敗するテストを追加**

```python
# portal_core/tests/test_departments.py に追加
def test_user_has_department_id(db_session):
    from portal_core.models.user import User
    cols = {c.name for c in User.__table__.columns}
    assert "department_id" in cols
    assert "group_id" not in cols


def test_user_response_has_department(client):
    resp = client.get("/api/auth/me")
    assert resp.status_code == 200
    data = resp.json()
    assert "department_id" in data
    assert "group_id" not in data
```

**Step 2: テスト失敗確認**
```bash
cd portal_core && pytest tests/test_departments.py::test_user_has_department_id -v
```
Expected: FAIL (group_id still exists, department_id not yet added)

**Step 3: User モデル更新**

`portal_core/portal_core/models/user.py`:
```python
# 変更前
group_id = Column(Integer, ForeignKey("groups.id", ondelete="SET NULL"), nullable=True, index=True)

# 変更後
department_id = Column(
    Integer,
    ForeignKey("departments.id", ondelete="SET NULL"),
    nullable=True,
    index=True,
)
```

**Step 4: User スキーマ更新**

`portal_core/portal_core/schemas/user.py`:
```python
# 変更前（UserResponse内）
group_id: Optional[int] = None
group_name: Optional[str] = None

# 変更後
department_id: Optional[int] = None
department_name: Optional[str] = None
```

**Step 5: User Service 更新**

`portal_core/portal_core/services/user_service.py`:
```python
# _build_group_map → _build_department_map
def _build_department_map(db):
    from portal_core.models.department import Department
    return {d.id: d.name for d in db.query(Department).all()}

# _to_response 内
def _to_response(user, department_map):
    return UserResponse(
        ...
        department_id=user.department_id,
        department_name=department_map.get(user.department_id),
        ...
    )
```

**Step 6: Group ファイル削除**

```bash
rm portal_core/portal_core/models/group.py
rm portal_core/portal_core/crud/group.py
rm portal_core/portal_core/schemas/group.py
rm portal_core/portal_core/services/group_service.py
rm portal_core/portal_core/routers/api_groups.py
```

**Step 7: portal_core の `__init__.py` を全て整理**

各 `__init__.py` から `Group` 関連の import を削除。

**Step 8: portal_core テスト一式を実行**

```bash
cd portal_core && pytest tests/ -q
```

> 注意: `test_groups.py` はこのステップで削除する。`test_departments.py` に新しいテストが入っている。
> `test_users.py` の group_id 参照を department_id に更新する。

**Step 9: コミット**
```bash
git add -A
git commit -m "refactor: rename User.group_id to department_id, remove Group model from portal_core"
```

---

## Task 7: Alembic データ移行マイグレーション

**Files:**
- Create: `alembic/versions/XXXX_groups_to_departments.py`

**Step 1: マイグレーションファイル生成**
```bash
alembic revision -m "groups_to_departments"
```

**Step 2: マイグレーション内容を記述**

```python
# alembic/versions/XXXX_groups_to_departments.py
"""groups_to_departments

Revision ID: (自動生成)
Revises: 4671c277afb4
Create Date: 2026-02-27
"""
from alembic import op
import sqlalchemy as sa

revision = "(新しいID)"
down_revision = "4671c277afb4"
branch_labels = None
depends_on = None


def upgrade():
    # 1. departments テーブル作成
    op.create_table(
        "departments",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(100), nullable=False, unique=True),
        sa.Column("code", sa.String(50), nullable=True, unique=True),
        sa.Column("description", sa.String(500), nullable=True),
        sa.Column("parent_id", sa.Integer, sa.ForeignKey("departments.id", ondelete="SET NULL"), nullable=True, index=True),
        sa.Column("sort_order", sa.Integer, nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # 2. groups → departments データコピー
    op.execute(
        """
        INSERT INTO departments (id, name, description, sort_order, created_at, updated_at)
        SELECT id, name, description, sort_order, created_at, NOW()
        FROM groups
        """
    )

    # 3. シーケンスを groups と同期
    op.execute(
        """
        SELECT setval('departments_id_seq',
            COALESCE((SELECT MAX(id) FROM departments), 0) + 1, false)
        """
    )

    # 4. users に department_id を追加（一時的にNULL許可）
    op.add_column("users", sa.Column("department_id", sa.Integer, nullable=True))
    op.create_foreign_key(
        "fk_users_department_id",
        "users", "departments",
        ["department_id"], ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_users_department_id", "users", ["department_id"])

    # 5. users.group_id → users.department_id にコピー
    op.execute("UPDATE users SET department_id = group_id WHERE group_id IS NOT NULL")

    # 6. users.group_id 削除（FKを先に削除）
    op.drop_constraint("fk_users_group_id", "users", type_="foreignkey")
    op.drop_index("ix_users_group_id", "users")
    op.drop_column("users", "group_id")

    # 7. log_sources に department_id を追加（一時的にNULL許可）
    op.add_column("log_sources", sa.Column("department_id", sa.Integer, nullable=True))
    op.create_foreign_key(
        "fk_log_sources_department_id",
        "log_sources", "departments",
        ["department_id"], ["id"],
    )

    # 8. log_sources.group_id → log_sources.department_id にコピー
    op.execute(
        "UPDATE log_sources SET department_id = group_id WHERE group_id IS NOT NULL"
    )

    # 9. log_sources.department_id を NOT NULL に
    op.alter_column("log_sources", "department_id", nullable=False)

    # 10. log_sources.group_id 削除
    op.drop_constraint("fk_log_sources_group_id", "log_sources", type_="foreignkey")
    op.drop_column("log_sources", "group_id")

    # 11. groups テーブル削除
    op.drop_table("groups")


def downgrade():
    # groups テーブル復元、データコピー逆順で実施（省略可）
    raise NotImplementedError("Downgrade not supported for this migration")
```

> **注意**: FK 制約名は実際のDB上の名前に合わせること。確認コマンド:
> ```bash
> psql -d <DB_NAME> -c "\d users" | grep group_id
> psql -d <DB_NAME> -c "\d log_sources" | grep group_id
> ```

**Step 3: マイグレーション適用**
```bash
alembic upgrade head
```

**Step 4: DB確認**
```sql
\d departments
\d users        -- department_id があること、group_id がないこと
\d log_sources  -- department_id があること、group_id がないこと
```

**Step 5: コミット**
```bash
git add alembic/versions/
git commit -m "feat: add Alembic migration to migrate groups to departments"
```

---

## Task 8: app 側の LogSource モデル + シム更新

**Files:**
- Modify: `app/models/log_source.py`
- Modify: `app/schemas/log_source.py` (存在する場合)
- Modify: `app/models/group.py` (Department re-export shim に変更)
- Modify: `app/crud/group.py` (department CRUD re-export shim に変更)
- Modify: `app/services/group_service.py` (department_service re-export shim に変更)

**Step 1: LogSource モデル更新**

`app/models/log_source.py`:
```python
# 変更前
group_id = Column(Integer, ForeignKey("groups.id"), nullable=False)

# 変更後
department_id = Column(Integer, ForeignKey("departments.id"), nullable=False)
```

**Step 2: LogSource スキーマ更新**

`app/schemas/log_source.py` で `group_id` → `department_id`、`group_name` → `department_name` に更新。

**Step 3: app/models/group.py を shim に更新**

```python
# app/models/group.py
# Backward compat shim — Department を Group として再エクスポート
from portal_core.models.department import Department as Group  # noqa: F401

__all__ = ["Group"]
```

**Step 4: app/crud/group.py を shim に更新**

```python
# app/crud/group.py
from portal_core.crud.department import (  # noqa: F401
    get_departments as get_groups,
    create_department as create_group,
    update_department as update_group,
    delete_department as delete_group,
    count_department_members as count_members,
)
```

**Step 5: app/services/group_service.py を shim に更新**

```python
# app/services/group_service.py
from portal_core.services.department_service import (  # noqa: F401
    get_departments_svc as get_groups_svc,
    get_department_svc as get_group_svc,
    create_department_svc as create_group_svc,
    update_department_svc as update_group_svc,
    delete_department_svc as delete_group_svc,
)
```

**Step 6: app テスト実行（log_sources関連）**

```bash
pytest tests/test_log_sources.py -q
```

`group_id` → `department_id` に更新が必要なテストケースを修正する。

**Step 7: コミット**
```bash
git add app/models/ app/schemas/ app/crud/ app/services/
git commit -m "refactor: update LogSource and app shims for group → department rename"
```

---

## Task 9: Wiki + Summary + User CRUD 更新

**Files:**
- Modify: `app/services/wiki_service.py`
- Modify: `app/crud/wiki_page.py`
- Modify: `app/services/summary_service.py`
- Modify: `app/crud/user.py`

**Step 1: wiki_service.py 更新**

```python
# app/services/wiki_service.py
# 変更前
def _get_user_group_id(db: Session, user_id: int) -> Optional[int]:
    user = db.query(User).filter(User.id == user_id).first()
    return user.group_id if user else None

# 変更後
def _get_user_department_id(db: Session, user_id: int) -> Optional[int]:
    user = db.query(User).filter(User.id == user_id).first()
    return user.department_id if user else None
```

`_get_user_group_id` の呼び出し箇所を `_get_user_department_id` に全て更新。

**Step 2: wiki_page.py の raw SQL 更新**

`app/crud/wiki_page.py` 内の raw SQL:
```sql
-- 変更前
WHERE group_id = :user_group_id

-- 変更後
WHERE department_id = :user_department_id
```

パラメータ名 `user_group_id` → `user_department_id` も合わせて更新。

**Step 3: summary_service.py 更新**

`app/services/summary_service.py`:
```python
# group_id 参照を全て department_id に変更
# get_users_in_group → get_users_in_department
```

**Step 4: app/crud/user.py 更新**

```python
# 変更前
def get_users_in_group(db: Session, group_id: int, active_only: bool = False) -> List[User]:
    q = db.query(User).filter(User.group_id == group_id)
    ...

# 変更後
def get_users_in_department(db: Session, department_id: int, active_only: bool = False) -> List[User]:
    q = db.query(User).filter(User.department_id == department_id)
    ...
```

`summary_service.py` の呼び出し側も合わせて更新。

**Step 5: テスト実行**
```bash
pytest tests/test_wiki.py tests/test_summary.py -q
```

**Step 6: コミット**
```bash
git add app/services/wiki_service.py app/crud/wiki_page.py app/services/summary_service.py app/crud/user.py
git commit -m "refactor: update wiki/summary services for group → department rename"
```

---

## Task 10: テンプレート + JavaScript 更新

**Files:**
- Modify: `templates/summary.html`
- Modify: `templates/calendar.html`
- Modify: `templates/logs.html`
- Modify: JS ファイル（users.js, calendar.js, summary 関連 JS）

**Step 1: 実際のファイルを確認してから更新**

まず各ファイルを読んで `group_id`、`/api/groups/` の参照箇所を全て特定する。

```bash
grep -rn "group_id\|/api/groups\|group-filter\|groupId\|group_map" templates/ static/js/
grep -rn "group_id\|/api/groups\|group-filter\|groupId\|group_map" portal_core/portal_core/static/
```

**Step 2: `templates/summary.html` 更新**

```html
<!-- 変更前 -->
<select id="group-filter" ...>

<!-- 変更後 -->
<select id="department-filter" ...>
```

JS 側の `group_id` クエリパラメータ → `department_id` に変更。

**Step 3: `templates/calendar.html` 更新**

同様に `group-filter` → `department-filter`、`/api/groups/` → `/api/departments/`。

**Step 4: `templates/logs.html` 更新**

```html
<!-- 変更前 -->
<select id="source-group-id" ...>
    <option v-for="group in groups" :value="group.id">{{ group.name }}</option>

<!-- 変更後 -->
<select id="source-department-id" ...>
    <option v-for="dept in departments" :value="dept.id">{{ dept.name }}</option>
```

**Step 5: JS ファイル更新**

`/api/groups/` を呼んでいる全 JS ファイルを `/api/departments/` に変更。

`users.js` のグループ管理 UI をデパートメント管理 UI に更新:
- `createGroup` → `createDepartment`
- `updateGroup` → `updateDepartment`
- グループ選択に `parent_id` フィールドを追加（階層ツリー対応）

**Step 6: テスト実行（手動確認）**

```bash
python main.py
# ブラウザで /users, /summary, /calendar, /logs を確認
```

**Step 7: コミット**
```bash
git add templates/ static/js/ portal_core/portal_core/static/
git commit -m "feat: update templates and JS for groups → departments rename"
```

---

## Task 11: portal_core/tests 更新 + 旧 test_groups.py 削除

**Files:**
- Delete: `portal_core/tests/test_groups.py`
- Modify: `portal_core/tests/test_departments.py`（完成させる）
- Modify: `portal_core/tests/test_users.py`（department_id に更新）

**Step 1: test_groups.py を削除**
```bash
rm portal_core/tests/test_groups.py
```

**Step 2: test_users.py の group_id 参照を department_id に更新**

```python
# 変更前
resp = client.put(f"/api/users/{user_id}", json={"group_id": 1})
assert resp.json()["group_id"] == 1

# 変更後
resp = client.put(f"/api/users/{user_id}", json={"department_id": 1})
assert resp.json()["department_id"] == 1
```

**Step 3: portal_core テスト全件実行**

```bash
cd portal_core && pytest tests/ -q
```
Expected: 全テスト PASS（test_groups.py の分は test_departments.py でカバー済み）

**Step 4: app テスト全件実行**

```bash
pytest tests/ -q
```

**Step 5: lint + format**
```bash
ruff check --fix . && ruff format .
```

**Step 6: 最終コミット**
```bash
git add portal_core/tests/ tests/
git commit -m "test: replace test_groups with test_departments, update user tests"
```

---

## Task 12: 全テスト実行・最終確認

**Step 1: portal_core テスト**
```bash
cd portal_core && pytest tests/ -q && cd ..
```
Expected: 全 PASS

**Step 2: app テスト**
```bash
pytest tests/ -q
```
Expected: 全 PASS（既存2件の known failures を除く）

**Step 3: lint チェック**
```bash
ruff check --fix . && ruff format .
```

**Step 4: アプリ起動確認**
```bash
python main.py
# /users, /summary, /calendar, /logs を手動確認
```

---

## 注意事項

### FK 制約名の確認
マイグレーション実行前に実際の FK 制約名を確認:
```bash
psql -d <DB_NAME> -c "\d+ users"
psql -d <DB_NAME> -c "\d+ log_sources"
```
`groups` 関連の FK 制約名をメモして migration の `drop_constraint` に使用。

### known failures (既存)
以下の2件は既存の失敗で回帰ではない:
- `tests/test_attendances.py` — clock_in duplicate constraint
- `tests/test_summary.py` — category_trends assertion

### api/routers/api_groups.py の扱い
`app/routers/api_groups.py` が存在する場合: portal_core がすでに `/api/departments/` ルートを登録するため、app 側の shim ルーターは不要。削除またはコメントアウトする。

### ユーザー管理画面の group_id → department_id
`PUT /api/users/{id}` の `group_id` パラメータを `department_id` に変更。`portal_core/portal_core/schemas/user.py` の `UserUpdate` スキーマも更新が必要。
