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
