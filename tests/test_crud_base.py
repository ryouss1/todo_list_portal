"""Unit tests for CRUDBase generic class."""

import pytest
from pydantic import BaseModel

from app.crud.base import CRUDBase
from app.models.task_category import TaskCategory


class FakeCreate(BaseModel):
    name: str


class FakeUpdate(BaseModel):
    name: str = None

    model_config = {"extra": "forbid"}


_crud = CRUDBase(TaskCategory)


@pytest.fixture()
def category(db_session):
    """Create a test category."""
    cat = TaskCategory(name="TestCat")
    db_session.add(cat)
    db_session.commit()
    db_session.refresh(cat)
    return cat


# --- get ---


def test_get_existing(db_session, category):
    result = _crud.get(db_session, category.id)
    assert result is not None
    assert result.id == category.id
    assert result.name == "TestCat"


def test_get_nonexistent(db_session):
    result = _crud.get(db_session, 999999)
    assert result is None


# --- get_all ---


def test_get_all(db_session, category):
    results = _crud.get_all(db_session)
    ids = [r.id for r in results]
    assert category.id in ids


# --- create with schema ---


def test_create_with_schema(db_session):
    data = FakeCreate(name="SchemaCreated")
    result = _crud.create(db_session, data)
    assert result.id is not None
    assert result.name == "SchemaCreated"
    # Verify it's persisted
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
    # TaskCategory only has name, so we just verify extra_fields override works
    data = FakeCreate(name="Original")
    result = _crud.create(db_session, data, name="Overridden")
    assert result.name == "Overridden"


# --- create with commit=False ---


def test_create_no_commit(db_session):
    result = _crud.create(db_session, {"name": "FlushOnly"}, commit=False)
    assert result.id is not None  # flush assigns ID
    assert result.name == "FlushOnly"


# --- update with schema ---


def test_update_with_schema(db_session, category):
    data = FakeUpdate(name="Updated")
    result = _crud.update(db_session, category, data)
    assert result.name == "Updated"
    assert result.id == category.id


# --- update with dict ---


def test_update_with_dict(db_session, category):
    result = _crud.update(db_session, category, {"name": "DictUpdated"})
    assert result.name == "DictUpdated"


# --- update exclude_unset ---


def test_update_exclude_unset(db_session, category):
    """When using a schema with unset fields, only set fields are applied."""
    original_name = category.name
    data = FakeUpdate()  # name is not set (None default, but unset)
    result = _crud.update(db_session, category, data)
    assert result.name == original_name  # name unchanged because it was unset


# --- update with commit=False ---


def test_update_no_commit(db_session, category):
    result = _crud.update(db_session, category, {"name": "FlushUpdated"}, commit=False)
    assert result.name == "FlushUpdated"


# --- delete ---


def test_delete(db_session, category):
    cat_id = category.id
    _crud.delete(db_session, category)
    assert _crud.get(db_session, cat_id) is None


# --- delete with commit=False ---


def test_delete_no_commit(db_session, category):
    cat_id = category.id
    _crud.delete(db_session, category, commit=False)
    # After flush, the object should be marked for deletion
    result = db_session.query(TaskCategory).filter(TaskCategory.id == cat_id).first()
    assert result is None
