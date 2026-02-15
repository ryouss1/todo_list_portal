"""Tests for Task List feature (TaskListItem CRUD, assignment, start, time accumulation)."""

import pytest

from app.models.task_category import TaskCategory
from app.models.task_list_item import TaskListItem


@pytest.fixture()
def test_category(db_session):
    """Create a test category for FK references."""
    cat = TaskCategory(name="Test Category")
    db_session.add(cat)
    db_session.flush()
    return cat


# ─── CRUD Tests ───


def test_create_item(client):
    res = client.post("/api/task-list/", json={"title": "Test Item"})
    assert res.status_code == 201
    data = res.json()
    assert data["title"] == "Test Item"
    assert data["status"] == "open"
    assert data["total_seconds"] == 0
    assert data["created_by"] == 1
    assert data["assignee_id"] is None


def test_create_item_with_all_fields(client, test_category):
    res = client.post(
        "/api/task-list/",
        json={
            "title": "Full Item",
            "description": "Description text",
            "scheduled_date": "2026-03-01",
            "category_id": test_category.id,
            "backlog_ticket_id": "WHT-100",
        },
    )
    assert res.status_code == 201
    data = res.json()
    assert data["description"] == "Description text"
    assert data["scheduled_date"] == "2026-03-01"
    assert data["category_id"] == test_category.id
    assert data["backlog_ticket_id"] == "WHT-100"


def test_create_item_title_required(client):
    res = client.post("/api/task-list/", json={})
    assert res.status_code == 422


def test_get_item(client):
    res = client.post("/api/task-list/", json={"title": "Get Me"})
    item_id = res.json()["id"]
    res = client.get(f"/api/task-list/{item_id}")
    assert res.status_code == 200
    assert res.json()["title"] == "Get Me"


def test_update_item(client):
    res = client.post("/api/task-list/", json={"title": "Original"})
    item_id = res.json()["id"]
    res = client.put(f"/api/task-list/{item_id}", json={"title": "Updated"})
    assert res.status_code == 200
    assert res.json()["title"] == "Updated"


def test_update_status(client):
    res = client.post("/api/task-list/", json={"title": "Status Test"})
    item_id = res.json()["id"]
    res = client.put(f"/api/task-list/{item_id}", json={"status": "done"})
    assert res.status_code == 200
    assert res.json()["status"] == "done"


def test_delete_item(client):
    res = client.post("/api/task-list/", json={"title": "Delete Me"})
    item_id = res.json()["id"]
    res = client.delete(f"/api/task-list/{item_id}")
    assert res.status_code == 204
    res = client.get(f"/api/task-list/{item_id}")
    assert res.status_code == 404


# ─── List All Tests ───


def test_list_all_shows_everything(client, db_session, other_user):
    # Create items: one unassigned, one assigned to user1, one assigned to user2
    client.post("/api/task-list/", json={"title": "Unassigned Item"})
    client.post("/api/task-list/", json={"title": "My Item", "assignee_id": 1})
    item3 = TaskListItem(title="Other Item", created_by=2, assignee_id=2)
    db_session.add(item3)
    db_session.flush()

    res = client.get("/api/task-list/all")
    assert res.status_code == 200
    titles = [i["title"] for i in res.json()]
    assert "Unassigned Item" in titles
    assert "My Item" in titles
    assert "Other Item" in titles


def test_list_all_filter_by_user(client, db_session, other_user):
    client.post("/api/task-list/", json={"title": "User1 Item", "assignee_id": 1})
    item2 = TaskListItem(title="User2 Item", created_by=2, assignee_id=2)
    db_session.add(item2)
    db_session.flush()

    res = client.get("/api/task-list/all?assignee_id=1")
    assert res.status_code == 200
    titles = [i["title"] for i in res.json()]
    assert "User1 Item" in titles
    assert "User2 Item" not in titles


def test_list_all_filter_unassigned(client):
    client.post("/api/task-list/", json={"title": "Pool Item"})
    client.post("/api/task-list/", json={"title": "Assigned Item", "assignee_id": 1})

    res = client.get("/api/task-list/all?assignee_id=0")
    assert res.status_code == 200
    titles = [i["title"] for i in res.json()]
    assert "Pool Item" in titles
    assert "Assigned Item" not in titles


# ─── Assignment Tests ───


def test_unassigned_list(client):
    client.post("/api/task-list/", json={"title": "Pool Item"})
    res = client.get("/api/task-list/unassigned")
    assert res.status_code == 200
    titles = [i["title"] for i in res.json()]
    assert "Pool Item" in titles


def test_assign_moves_to_mine(client):
    res = client.post("/api/task-list/", json={"title": "Assign Me"})
    item_id = res.json()["id"]

    res = client.post(f"/api/task-list/{item_id}/assign")
    assert res.status_code == 200
    assert res.json()["assignee_id"] == 1

    # Should appear in mine
    res = client.get("/api/task-list/mine")
    ids = [i["id"] for i in res.json()]
    assert item_id in ids

    # Should not appear in unassigned
    res = client.get("/api/task-list/unassigned")
    ids = [i["id"] for i in res.json()]
    assert item_id not in ids


def test_unassign_returns_to_pool(client):
    res = client.post("/api/task-list/", json={"title": "Unassign Me"})
    item_id = res.json()["id"]
    client.post(f"/api/task-list/{item_id}/assign")

    res = client.post(f"/api/task-list/{item_id}/unassign")
    assert res.status_code == 200
    assert res.json()["assignee_id"] is None


def test_assign_already_assigned_by_other_forbidden(client, db_session, other_user):
    item = TaskListItem(title="Taken", created_by=1, assignee_id=2)
    db_session.add(item)
    db_session.flush()

    res = client.post(f"/api/task-list/{item.id}/assign")
    assert res.status_code == 403


# ─── Sub-task Tests ───


# ─── Start as Task Tests ───


def test_start_creates_task(client, test_category):
    res = client.post(
        "/api/task-list/",
        json={
            "title": "Start Me",
            "description": "Desc",
            "category_id": test_category.id,
            "backlog_ticket_id": "WHT-99",
        },
    )
    item_id = res.json()["id"]

    res = client.post(f"/api/task-list/{item_id}/start")
    assert res.status_code == 200
    task = res.json()
    assert task["title"] == "Start Me"
    assert task["description"] == "Desc"
    assert task["category_id"] == test_category.id
    assert task["backlog_ticket_id"] == "WHT-99"
    assert task["source_item_id"] == item_id


def test_start_sets_item_in_progress(client):
    res = client.post("/api/task-list/", json={"title": "Status Check"})
    item_id = res.json()["id"]

    client.post(f"/api/task-list/{item_id}/start")

    res = client.get(f"/api/task-list/{item_id}")
    assert res.json()["status"] == "in_progress"


def test_start_multiple_times(client):
    res = client.post("/api/task-list/", json={"title": "Multi Start"})
    item_id = res.json()["id"]

    res1 = client.post(f"/api/task-list/{item_id}/start")
    assert res1.status_code == 200
    res2 = client.post(f"/api/task-list/{item_id}/start")
    assert res2.status_code == 200
    assert res1.json()["id"] != res2.json()["id"]


# ─── Time Accumulation Tests ───


def test_done_accumulates_time_to_source(client, db_session):
    # Create item
    res = client.post("/api/task-list/", json={"title": "Time Test"})
    item_id = res.json()["id"]

    # Start as task
    res = client.post(f"/api/task-list/{item_id}/start")
    task_id = res.json()["id"]

    # Manually set total_seconds on the task (simulating timer)
    from app.models.task import Task

    task = db_session.query(Task).filter(Task.id == task_id).first()
    task.total_seconds = 3600
    db_session.flush()

    # Done the task
    res = client.post(f"/api/tasks/{task_id}/done")
    assert res.status_code == 204

    # Check source item accumulated time
    res = client.get(f"/api/task-list/{item_id}")
    assert res.json()["total_seconds"] == 3600


def test_done_source_item_not_deleted(client, db_session):
    res = client.post("/api/task-list/", json={"title": "Survive Test"})
    item_id = res.json()["id"]

    res = client.post(f"/api/task-list/{item_id}/start")
    task_id = res.json()["id"]

    client.post(f"/api/tasks/{task_id}/done")

    # Source item should still exist
    res = client.get(f"/api/task-list/{item_id}")
    assert res.status_code == 200


# ─── Authorization Tests ───


def test_other_user_assigned_item_not_visible(client, db_session, other_user):
    item = TaskListItem(title="Private", created_by=2, assignee_id=2)
    db_session.add(item)
    db_session.flush()

    res = client.get(f"/api/task-list/{item.id}")
    assert res.status_code == 404


def test_creator_can_see_assigned_item(db_session, other_user, client_user2, client):
    # User 1 creates, user 2 is assigned
    item = TaskListItem(title="Creator Access", created_by=1, assignee_id=2)
    db_session.add(item)
    db_session.flush()

    res = client.get(f"/api/task-list/{item.id}")
    assert res.status_code == 200


def test_create_item_with_assignee(client):
    res = client.post("/api/task-list/", json={"title": "Pre-Assign", "assignee_id": 1})
    assert res.status_code == 201
    assert res.json()["assignee_id"] == 1


def test_page_accessible(client):
    res = client.get("/task-list")
    assert res.status_code == 200
