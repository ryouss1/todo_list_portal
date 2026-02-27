"""Unit tests for CRUDBase generic class (portal_core).

Uses Department model (core model) instead of Group (removed) or TaskCategory (app-specific).
"""

import pytest
from pydantic import BaseModel

from portal_core.crud.base import CRUDBase
from portal_core.models.department import Department


class FakeCreate(BaseModel):
    name: str


class FakeUpdate(BaseModel):
    name: str = None

    model_config = {"extra": "forbid"}


_crud = CRUDBase(Department)


@pytest.fixture()
def dept(db_session):
    """Create a test department."""
    d = Department(name="TestDept")
    db_session.add(d)
    db_session.commit()
    db_session.refresh(d)
    return d


# --- get ---


def test_get_existing(db_session, dept):
    result = _crud.get(db_session, dept.id)
    assert result is not None
    assert result.id == dept.id
    assert result.name == "TestDept"


def test_get_nonexistent(db_session):
    result = _crud.get(db_session, 999999)
    assert result is None


# --- get_all ---


def test_get_all(db_session, dept):
    results = _crud.get_all(db_session)
    ids = [r.id for r in results]
    assert dept.id in ids


# --- create with schema ---


def test_create_with_schema(db_session):
    data = FakeCreate(name="SchemaCreated")
    result = _crud.create(db_session, data)
    assert result.id is not None
    assert result.name == "SchemaCreated"
    fetched = _crud.get(db_session, result.id)
    assert fetched is not None


# --- create with dict ---


def test_create_with_dict(db_session):
    result = _crud.create(db_session, {"name": "DictCreated"})
    assert result.id is not None
    assert result.name == "DictCreated"


# --- create with extra_fields ---


def test_create_with_extra_fields(db_session):
    """Extra fields are merged into the data dict before creating the model."""
    data = FakeCreate(name="Original")
    result = _crud.create(db_session, data, name="Overridden")
    assert result.name == "Overridden"


# --- create with commit=False ---


def test_create_no_commit(db_session):
    result = _crud.create(db_session, {"name": "FlushOnly"}, commit=False)
    assert result.id is not None
    assert result.name == "FlushOnly"


# --- update with schema ---


def test_update_with_schema(db_session, dept):
    data = FakeUpdate(name="Updated")
    result = _crud.update(db_session, dept, data)
    assert result.name == "Updated"
    assert result.id == dept.id


# --- update with dict ---


def test_update_with_dict(db_session, dept):
    result = _crud.update(db_session, dept, {"name": "DictUpdated"})
    assert result.name == "DictUpdated"


# --- update exclude_unset ---


def test_update_exclude_unset(db_session, dept):
    """When using a schema with unset fields, only set fields are applied."""
    original_name = dept.name
    data = FakeUpdate()
    result = _crud.update(db_session, dept, data)
    assert result.name == original_name


# --- update with commit=False ---


def test_update_no_commit(db_session, dept):
    result = _crud.update(db_session, dept, {"name": "FlushUpdated"}, commit=False)
    assert result.name == "FlushUpdated"


# --- delete ---


def test_delete(db_session, dept):
    dept_id = dept.id
    _crud.delete(db_session, dept)
    assert _crud.get(db_session, dept_id) is None


# --- delete with commit=False ---


def test_delete_no_commit(db_session, dept):
    dept_id = dept.id
    _crud.delete(db_session, dept, commit=False)
    result = db_session.query(Department).filter(Department.id == dept_id).first()
    assert result is None


# --- get_db rollback ---


class TestGetDbRollback:
    def test_get_db_calls_rollback_on_exception(self):
        """get_db() should explicitly call rollback() when an exception is raised."""
        from unittest.mock import MagicMock, patch

        from portal_core.database import get_db

        mock_session = MagicMock()

        with patch("portal_core.database.SessionLocal", return_value=mock_session):
            gen = get_db()
            next(gen)  # advance to the yield

            # Throw an exception into the generator
            try:
                gen.throw(RuntimeError("test exception"))
            except RuntimeError:
                pass

        # rollback() must have been called before close()
        call_names = [c[0] for c in mock_session.method_calls]
        assert "rollback" in call_names, "db.rollback() was not called on exception"
        rollback_idx = call_names.index("rollback")
        close_idx = call_names.index("close")
        assert rollback_idx < close_idx, "rollback() must be called before close()"
