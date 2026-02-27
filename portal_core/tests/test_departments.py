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


def test_department_parent_id_self_reference():
    """parent_id の FK が departments テーブルを指すこと"""
    parent_id_col = Department.__table__.columns["parent_id"]
    fk = list(parent_id_col.foreign_keys)[0]
    assert "departments.id" in str(fk.target_fullname)
