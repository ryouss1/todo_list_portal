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
