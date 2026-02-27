from portal_core.models.department import Department


def test_department_model_columns():
    cols = {c.name for c in Department.__table__.columns}
    assert "id" in cols
    assert "name" in cols
    assert "code" in cols
    assert "description" in cols
    assert "parent_id" in cols
    assert "sort_order" in cols
    assert "is_active" in cols
    assert "created_at" in cols
    assert "updated_at" in cols


def test_department_tablename():
    assert Department.__tablename__ == "departments"


def test_department_parent_id_self_reference():
    """parent_id の FK が departments テーブルを指すこと"""
    parent_id_col = Department.__table__.columns["parent_id"]
    fk = list(parent_id_col.foreign_keys)[0]
    assert "departments.id" in str(fk.target_fullname)


def test_department_create_and_retrieve(db_session):
    """DB を使って Department を作成・取得できること"""
    dept = Department(name="Engineering", sort_order=0)
    db_session.add(dept)
    db_session.flush()

    assert dept.id is not None
    assert dept.is_active is True
    assert dept.parent_id is None
    assert dept.code is None

    retrieved = db_session.get(Department, dept.id)
    assert retrieved.name == "Engineering"


def test_department_defaults(db_session):
    """デフォルト値が正しく設定されること"""
    dept = Department(name="TestDept")
    db_session.add(dept)
    db_session.flush()

    assert dept.sort_order == 0
    assert dept.is_active is True
    assert dept.parent_id is None


def test_get_departments_empty(db_session):
    from portal_core.crud.department import get_departments

    result = get_departments(db_session)
    assert isinstance(result, list)


def test_create_and_get_department(db_session):
    from portal_core.crud.department import create_department, get_department

    dept = create_department(db_session, name="Engineering", sort_order=0)
    assert dept.id is not None
    assert dept.name == "Engineering"
    assert dept.is_active is True
    assert dept.parent_id is None

    retrieved = get_department(db_session, dept.id)
    assert retrieved.name == "Engineering"


def test_create_department_with_parent(db_session):
    from portal_core.crud.department import create_department

    parent = create_department(db_session, name="Technology", sort_order=0)
    child = create_department(db_session, name="Backend", parent_id=parent.id, sort_order=0)
    assert child.parent_id == parent.id


def test_update_department(db_session):
    from portal_core.crud.department import create_department, update_department

    dept = create_department(db_session, name="OldName")
    updated = update_department(db_session, dept, {"name": "NewName"})
    assert updated.name == "NewName"


def test_update_department_ignores_none(db_session):
    """None 値は無視され、既存の値が保持されること（仕様）"""
    from portal_core.crud.department import create_department, update_department

    dept = create_department(db_session, name="TestDept", description="original")
    update_department(db_session, dept, {"name": "Updated", "description": None})
    assert dept.name == "Updated"
    assert dept.description == "original"  # None で上書きされない


def test_delete_department(db_session):
    from portal_core.crud.department import create_department, delete_department, get_department

    dept = create_department(db_session, name="ToDelete")
    dept_id = dept.id
    delete_department(db_session, dept)
    assert get_department(db_session, dept_id) is None


def test_count_members(db_session):
    from portal_core.crud.department import count_members, create_department

    dept = create_department(db_session, name="HR", sort_order=0)
    # User テーブルには department_id がまだない（Task 6 で追加予定）
    # count が 0 であることだけ確認
    count = count_members(db_session, dept.id)
    assert count == 0


def test_get_departments_active(db_session):
    from portal_core.crud.department import create_department, get_departments_active

    _active = create_department(db_session, name="ActiveDept", is_active=True)
    _inactive = create_department(db_session, name="InactiveDept", is_active=False)

    result = get_departments_active(db_session)
    names = [d.name for d in result]
    assert "ActiveDept" in names
    assert "InactiveDept" not in names


def test_department_response_schema():
    from datetime import datetime

    from portal_core.schemas.department import DepartmentResponse

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


def test_department_create_schema():
    from portal_core.schemas.department import DepartmentCreate

    data = DepartmentCreate(name="HR")
    assert data.name == "HR"
    assert data.parent_id is None
    assert data.is_active is True
    assert data.sort_order == 0


def test_department_update_schema():
    from portal_core.schemas.department import DepartmentUpdate

    # 全フィールドが Optional であること
    data = DepartmentUpdate()
    assert data.name is None
    assert data.is_active is None


def test_department_service_create(db_session):
    from portal_core.schemas.department import DepartmentCreate
    from portal_core.services.department_service import (
        create_department_svc,
        get_departments_svc,
    )

    data = DepartmentCreate(name="Sales")
    dept = create_department_svc(db_session, data)
    assert dept.id is not None

    all_depts = get_departments_svc(db_session)
    assert any(d.name == "Sales" for d in all_depts)


def test_department_service_conflict(db_session):
    import pytest

    from portal_core.core.exceptions import ConflictError
    from portal_core.schemas.department import DepartmentCreate
    from portal_core.services.department_service import create_department_svc

    data = DepartmentCreate(name="UniqueTest")
    create_department_svc(db_session, data)
    with pytest.raises(ConflictError):
        create_department_svc(db_session, DepartmentCreate(name="UniqueTest"))


def test_department_service_not_found(db_session):
    import pytest

    from portal_core.core.exceptions import NotFoundError
    from portal_core.services.department_service import get_department_svc

    with pytest.raises(NotFoundError):
        get_department_svc(db_session, 99999)


def test_service_get_departments_returns_list(db_session):
    from portal_core.schemas.department import DepartmentCreate
    from portal_core.services.department_service import (
        create_department_svc,
        get_departments_svc,
    )

    create_department_svc(db_session, DepartmentCreate(name="SvcListDept"))
    result = get_departments_svc(db_session)
    assert isinstance(result, list)
    assert any(d.name == "SvcListDept" for d in result)


def test_service_get_department_by_id(db_session):
    from portal_core.schemas.department import DepartmentCreate
    from portal_core.services.department_service import (
        create_department_svc,
        get_department_svc,
    )

    dept = create_department_svc(db_session, DepartmentCreate(name="SvcGetDept"))
    fetched = get_department_svc(db_session, dept.id)
    assert fetched.id == dept.id
    assert fetched.name == "SvcGetDept"


def test_service_update_department_name(db_session):
    from portal_core.schemas.department import DepartmentCreate, DepartmentUpdate
    from portal_core.services.department_service import (
        create_department_svc,
        get_department_svc,
        update_department_svc,
    )

    dept = create_department_svc(db_session, DepartmentCreate(name="OldSvcName"))
    updated = update_department_svc(db_session, dept.id, DepartmentUpdate(name="NewSvcName"))
    assert updated.name == "NewSvcName"

    refetched = get_department_svc(db_session, dept.id)
    assert refetched.name == "NewSvcName"


def test_service_update_department_name_conflict(db_session):
    import pytest

    from portal_core.core.exceptions import ConflictError
    from portal_core.schemas.department import DepartmentCreate, DepartmentUpdate
    from portal_core.services.department_service import (
        create_department_svc,
        update_department_svc,
    )

    create_department_svc(db_session, DepartmentCreate(name="ConflictTarget"))
    dept2 = create_department_svc(db_session, DepartmentCreate(name="ConflictSource"))
    with pytest.raises(ConflictError):
        update_department_svc(db_session, dept2.id, DepartmentUpdate(name="ConflictTarget"))


def test_service_delete_department(db_session):
    import pytest

    from portal_core.core.exceptions import NotFoundError
    from portal_core.schemas.department import DepartmentCreate
    from portal_core.services.department_service import (
        create_department_svc,
        delete_department_svc,
        get_department_svc,
    )

    dept = create_department_svc(db_session, DepartmentCreate(name="SvcDeleteDept"))
    dept_id = dept.id
    delete_department_svc(db_session, dept_id)
    with pytest.raises(NotFoundError):
        get_department_svc(db_session, dept_id)
